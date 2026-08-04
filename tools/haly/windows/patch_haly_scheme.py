#!/usr/bin/env python3
# Copyright (c) 2026 The Haly Authors.
"""Inspect or patch prebuilt Brave PE images for the Haly UI scheme.

All replacements are length-preserving. Use --report-all --dry-run to inspect
candidate occurrences before enabling token replacement. URL-only replacement
is safer because it cannot modify unrelated exact-word "brave" strings.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import tempfile
from dataclasses import dataclass


@dataclass(frozen=True)
class Replacement:
    name: str
    source: bytes
    target: bytes
    token: bool = False


REPLACEMENTS = (
    Replacement("ASCII URL", b"brave://", b"haly://\x00"),
    Replacement(
        "UTF-16 URL",
        "brave://".encode("utf-16-le"),
        "haly://\0".encode("utf-16-le"),
    ),
    Replacement("ASCII token", b"brave\x00", b"haly\x00\x00", token=True),
    Replacement(
        "UTF-16 token",
        "brave\0".encode("utf-16-le"),
        "haly\0\0".encode("utf-16-le"),
        token=True,
    ),
)

PE_SUFFIXES = {".dll", ".exe"}


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(data)
        temporary_path = pathlib.Path(handle.name)
    os.replace(temporary_path, path)


def printable_context(raw: bytes, offset: int, length: int, radius: int = 56) -> str:
    start = max(0, offset - radius)
    end = min(len(raw), offset + length + radius)
    chunk = raw[start:end]
    return "".join(chr(byte) if 32 <= byte < 127 else "." for byte in chunk)


def occurrence_offsets(raw: bytes, needle: bytes):
    offset = 0
    while True:
        offset = raw.find(needle, offset)
        if offset < 0:
            return
        yield offset
        offset += len(needle)


def patch_file(
    path: pathlib.Path,
    *,
    dry_run: bool,
    report_all: bool,
    urls_only: bool,
) -> dict[str, int]:
    raw = path.read_bytes()
    patched = raw
    counts: dict[str, int] = {}

    for replacement in REPLACEMENTS:
        if urls_only and replacement.token:
            counts[replacement.name] = 0
            continue
        if len(replacement.source) != len(replacement.target):
            raise AssertionError(f"{replacement.name} is not length-preserving")

        offsets = list(occurrence_offsets(patched, replacement.source))
        counts[replacement.name] = len(offsets)
        if offsets:
            shown_offsets = offsets if report_all else offsets[:1]
            for offset in shown_offsets:
                print(
                    f"[Haly scheme] {path}: {replacement.name} "
                    f"offset=0x{offset:x} context="
                    f"{printable_context(patched, offset, len(replacement.source))!r}"
                )
            if not report_all and len(offsets) > 1:
                print(
                    f"[Haly scheme] {path}: {replacement.name} total={len(offsets)}"
                )
            patched = patched.replace(replacement.source, replacement.target)

    if patched != raw and not dry_run:
        atomic_write(path, patched)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-all", action="store_true")
    parser.add_argument(
        "--urls-only",
        action="store_true",
        help="patch only exact brave:// URL strings, not plain brave tokens",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")

    totals = {replacement.name: 0 for replacement in REPLACEMENTS}
    changed_files = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in PE_SUFFIXES:
            continue
        counts = patch_file(
            path,
            dry_run=args.dry_run,
            report_all=args.report_all,
            urls_only=args.urls_only,
        )
        if any(counts.values()):
            changed_files += 1
        for name, count in counts.items():
            totals[name] += count

    print(f"[Haly scheme] candidate PE files changed: {changed_files}")
    for name, count in totals.items():
        print(f"[Haly scheme] {name}: {count}")

    url_count = totals["ASCII URL"] + totals["UTF-16 URL"]
    if url_count == 0:
        raise SystemExit("No brave:// URL literal was found in the PE payload.")

    if not args.urls_only:
        token_count = totals["ASCII token"] + totals["UTF-16 token"]
        if token_count == 0:
            raise SystemExit("No exact brave token was found in the PE payload.")
        if token_count > 512:
            raise SystemExit(
                f"Refusing to patch an unexpectedly large number of tokens: {token_count}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
