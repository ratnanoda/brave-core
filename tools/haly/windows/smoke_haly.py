#!/usr/bin/env python3
# Copyright (c) 2026 The Haly Authors.
"""CDP smoke tests for an unpacked Haly/Brave Windows payload."""

from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import socket
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

import websocket

BAD_MARKERS = (
    "RESULT_CODE_KILLED_BAD_MESSAGE",
    "Aw, Snap",
    "このページを開けません",
    "sad tab",
)

INTERNAL_URL_PREFIXES = {
    # Brave internally canonicalizes some of its WebUI pages to chrome:// when
    # they are observed through CDP. Both forms represent a successful load.
    "version": ("brave://version", "chrome://version"),
    "newtab": (
        "brave://newtab",
        "chrome://newtab",
        "chrome://new-tab-page",
        "about:newtab",
    ),
}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def read_json(url: str, *, method: str = "GET"):
    request = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_debugger(port: int, process: subprocess.Popen, timeout: float = 30.0):
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/json/version"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"browser exited before DevTools became available: {process.returncode}"
            )
        try:
            return read_json(url)
        except Exception as error:  # noqa: BLE001 - diagnostic retry loop
            last_error = error
            time.sleep(0.25)
    raise RuntimeError(f"DevTools did not start: {last_error}")


class CdpSession:
    def __init__(self, websocket_url: str):
        self.socket = websocket.create_connection(
            websocket_url,
            timeout=10,
            origin="http://127.0.0.1",
            suppress_origin=True,
        )
        self.next_id = 1

    def close(self):
        self.socket.close()

    def command(self, method: str, params: dict | None = None, timeout: float = 15.0):
        command_id = self.next_id
        self.next_id += 1
        self.socket.send(
            json.dumps(
                {
                    "id": command_id,
                    "method": method,
                    "params": params or {},
                }
            )
        )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.socket.settimeout(max(0.1, deadline - time.monotonic()))
            message = json.loads(self.socket.recv())
            if message.get("id") != command_id:
                continue
            if "error" in message:
                raise RuntimeError(f"CDP {method} failed: {message['error']}")
            return message.get("result", {})
        raise TimeoutError(f"CDP command timed out: {method}")


def create_target(port: int, url: str):
    encoded = urllib.parse.quote(url, safe=":/?=&,%<>+-_")
    return read_json(f"http://127.0.0.1:{port}/json/new?{encoded}", method="PUT")


def close_target(port: int, target_id: str):
    try:
        read_json(f"http://127.0.0.1:{port}/json/close/{target_id}")
    except Exception:
        pass


def test_page(port: int, name: str, url: str, output_directory: pathlib.Path):
    target = create_target(port, "about:blank")
    target_id = target["id"]
    session = CdpSession(target["webSocketDebuggerUrl"])
    try:
        session.command("Page.enable")
        session.command("Runtime.enable")
        session.command("Page.navigate", {"url": url})

        deadline = time.monotonic() + 20.0
        value = None
        last_exception = None
        while time.monotonic() < deadline:
            try:
                result = session.command(
                    "Runtime.evaluate",
                    {
                        "expression": """
                            (() => ({
                              url: location.href,
                              title: document.title,
                              readyState: document.readyState,
                              text: (document.body?.innerText || '').slice(0, 8000),
                              html: (document.documentElement?.outerHTML || '').slice(0, 30000)
                            }))()
                        """,
                        "returnByValue": True,
                    },
                    timeout=5.0,
                )
                value = result.get("result", {}).get("value")
                if value and value.get("readyState") in {"interactive", "complete"}:
                    break
            except Exception as error:  # noqa: BLE001 - retry while page starts
                last_exception = error
            time.sleep(0.25)

        if not value:
            raise RuntimeError(f"{name}: no DOM result ({last_exception})")

        combined = "\n".join(
            str(value.get(field, "")) for field in ("url", "title", "text", "html")
        )
        for marker in BAD_MARKERS:
            if marker.lower() in combined.lower():
                raise RuntimeError(f"{name}: detected browser error marker {marker!r}")

        actual_url = str(value.get("url", ""))
        if name == "renderer" and not actual_url.startswith("data:text/html"):
            raise RuntimeError(f"{name}: unexpected URL {actual_url!r}")
        if name in INTERNAL_URL_PREFIXES and not actual_url.startswith(
            INTERNAL_URL_PREFIXES[name]
        ):
            raise RuntimeError(f"{name}: unexpected internal URL {actual_url!r}")

        screenshot = session.command("Page.captureScreenshot", {"format": "png"})
        image = base64.b64decode(screenshot["data"])
        screenshot_path = output_directory / f"{name}.png"
        screenshot_path.write_bytes(image)

        print(
            json.dumps(
                {
                    "name": name,
                    "url": actual_url,
                    "title": value.get("title", ""),
                    "readyState": value.get("readyState", ""),
                    "screenshotBytes": len(image),
                },
                ensure_ascii=False,
            )
        )

        # A nearly blank, highly compressible page can legitimately produce a
        # PNG well below 4 KiB. The PNG signature and a modest payload are
        # enough here because DOM content and browser error markers are checked
        # separately above.
        if not image.startswith(b"\x89PNG\r\n\x1a\n") or len(image) < 256:
            raise RuntimeError(f"{name}: screenshot is invalid or unexpectedly small")
    finally:
        session.close()
        close_target(port, target_id)


def stop_process_tree(process: subprocess.Popen):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("browser", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    browser = args.browser.resolve()
    if not browser.is_file():
        parser.error(f"browser executable not found: {browser}")
    args.output.mkdir(parents=True, exist_ok=True)

    port = free_port()
    profile = pathlib.Path(tempfile.mkdtemp(prefix="haly-cdp-smoke-"))
    stderr_path = args.output / "browser-stderr.txt"

    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-breakpad",
        "--disable-crash-reporter",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "about:blank",
    ]

    with stderr_path.open("wb") as stderr:
        process = subprocess.Popen(
            command,
            cwd=browser.parent,
            stdout=subprocess.DEVNULL,
            stderr=stderr,
        )
        try:
            version = wait_for_debugger(port, process)
            print(json.dumps({"devtools": version}, ensure_ascii=False))
            test_page(
                port,
                "renderer",
                "data:text/html,<title>HalySmoke</title><p>OK</p>",
                args.output,
            )
            test_page(port, "version", "brave://version/", args.output)
            test_page(port, "newtab", "brave://newtab/", args.output)
        finally:
            stop_process_tree(process)

    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    for marker in BAD_MARKERS:
        if marker.lower() in stderr_text.lower():
            raise RuntimeError(f"browser stderr contains {marker!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
