#!/usr/bin/env python3
# Copyright (c) 2026 The Haly Authors.
"""Patch prebuilt Brave PE images so the internal UI scheme is haly://.

Every replacement is length-preserving, so PE section offsets and relocation
records remain unchanged. The official signature must be checked before this
script runs; modifying the image necessarily invalidates that signature.
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


REPLACEMENTS = (
    Replacement("ASCII URL", b"brave://", b"haly://\x00"),
    Replacement(
        "UTF-16 URL",
        "brave://".encode("utf-16-le"),
        "haly://\0".encode("utf-16-le"),
    ),
    Replacement("ASCII token", b"brave\x00", b"haly\x00\x00"),
    Replacement(
        "UTF-16 token",
        "brave\0".encode("utf-16-le"),
        "haly\0\0".encode("utf-16-le"),
    ),
)

PE_SUFFIXES = {".dll", ".exe"}


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(data)
        temporary_path = pathlib.Path(handle.name)
    os.replace(temporary_path, path)


def printable_context(raw: bytes, offset: int, length: int) -> str:
    start = max(0, offset - 24)
    end = min(len(raw), offset + length + 24)
    chunk = raw[start:end]
    return "".join(chr(byte) if 32 <= byte < 127 else "." for byte in chunk)


def patch_file(path: pathlib.Path, *, dry_run: bool) -> dict[str, int]:
    raw = path.read_bytes()
    patched = raw
    counts: dict[str, int] = {}

    for replacement in REPLACEMENTS:
        if len(replacement.source) != len(replacement.target):
            raise AssertionError(f"{replacement.name} is not length-preserving")

        count = patched.count(replacement.source)
        counts[replacement.name] = count
        if count:
            first_offset = patched.find(replacement.source)
            print(
                f"[Haly scheme] {path}: {replacement.name} x{count}; "
                f"first context={printable_context(patched, first_offset, len(replacement.source))!r}"
            )
            patched = patched.replace(replacement.source, replacement.target)

    if patched != raw and not dry_run:
        atomic_write(path, patched)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")

    totals = {replacement.name: 0 for replacement in REPLACEMENTS}
    changed_files = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in PE_SUFFIXES:
            continue
        counts = patch_file(path, dry_run=args.dry_run)
        if any(counts.values()):
            changed_files += 1
        for name, count in counts.items():
            totals[name] += count

    print(f"[Haly scheme] candidate PE files changed: {changed_files}")
    for name, count in totals.items():
        print(f"[Haly scheme] {name}: {count}")

    token_count = totals["ASCII token"] + totals["UTF-16 token"]
    if token_count == 0:
        raise SystemExit("No exact brave scheme token was found in the PE payload.")
    if token_count > 512:
        raise SystemExit(
            f"Refusing to patch an unexpectedly large number of scheme tokens: {token_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
