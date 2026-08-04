#!/usr/bin/env python3
# Copyright (c) 2026 The Haly Authors.
# Use of this source code is governed by the BSD-style license found in the
# Chromium project. The DataPack layout implemented here follows Chromium's
# tools/grit/grit/format/data_pack.py.

from __future__ import annotations

import argparse
import gzip
import os
import pathlib
import struct
import tempfile
from dataclasses import dataclass


UTF8_REPLACEMENTS = (
    (b"Brave", b"Haly"),
    (b"BRAVE", b"HALY"),
)
UTF16_REPLACEMENTS = tuple(
    (source.decode("ascii").encode("utf-16-le"), target.decode("ascii").encode("utf-16-le"))
    for source, target in UTF8_REPLACEMENTS
)
TEXT_SUFFIXES = {
    ".css",
    ".desktop",
    ".htm",
    ".html",
    ".ini",
    ".json",
    ".manifest",
    ".properties",
    ".txt",
    ".xml",
}


@dataclass(frozen=True)
class DataPack:
    version: int
    encoding: int
    resources: list[tuple[int, bytes]]
    aliases: list[tuple[int, int]]


def replace_brand_bytes(payload: bytes) -> bytes:
    output = payload
    for source, target in UTF8_REPLACEMENTS + UTF16_REPLACEMENTS:
        output = output.replace(source, target)
    return output


def patch_resource(payload: bytes) -> bytes:
    if payload.startswith(b"\x1f\x8b"):
        try:
            expanded = gzip.decompress(payload)
        except (OSError, EOFError):
            return replace_brand_bytes(payload)
        patched = replace_brand_bytes(expanded)
        if patched == expanded:
            return payload
        return gzip.compress(patched, compresslevel=9, mtime=0)
    return replace_brand_bytes(payload)


def read_data_pack(raw: bytes) -> DataPack:
    if len(raw) < 9:
        raise ValueError("file is too small to be a Chromium data pack")

    version = struct.unpack_from("<I", raw, 0)[0]
    if version == 4:
        resource_count, encoding = struct.unpack_from("<IB", raw, 4)
        alias_count = 0
        header_size = 9
    elif version == 5:
        encoding, resource_count, alias_count = struct.unpack_from("<BxxxHH", raw, 4)
        header_size = 12
    else:
        raise ValueError(f"unsupported Chromium data pack version: {version}")

    entry_size = 6
    index_end = header_size + (resource_count + 1) * entry_size
    alias_end = index_end + alias_count * 4
    if alias_end > len(raw):
        raise ValueError("truncated Chromium data pack index")

    entries: list[tuple[int, int]] = []
    for index in range(resource_count + 1):
        resource_id, offset = struct.unpack_from("<HI", raw, header_size + index * entry_size)
        entries.append((resource_id, offset))

    resources: list[tuple[int, bytes]] = []
    previous_offset = -1
    for index in range(resource_count):
        resource_id, start = entries[index]
        _, end = entries[index + 1]
        if start < alias_end or end < start or end > len(raw) or start < previous_offset:
            raise ValueError("invalid Chromium data pack offsets")
        resources.append((resource_id, raw[start:end]))
        previous_offset = start

    aliases: list[tuple[int, int]] = []
    for index in range(alias_count):
        alias_id, target_index = struct.unpack_from("<HH", raw, index_end + index * 4)
        if target_index >= resource_count:
            raise ValueError("invalid Chromium data pack alias")
        aliases.append((alias_id, target_index))

    return DataPack(version, encoding, resources, aliases)


def write_data_pack(pack: DataPack) -> bytes:
    resource_count = len(pack.resources)
    alias_count = len(pack.aliases)

    if pack.version == 4:
        if alias_count:
            raise ValueError("version 4 data packs cannot contain aliases")
        header = struct.pack("<IIB", 4, resource_count, pack.encoding)
    elif pack.version == 5:
        header = struct.pack("<IBxxxHH", 5, pack.encoding, resource_count, alias_count)
    else:
        raise ValueError(f"unsupported Chromium data pack version: {pack.version}")

    data_offset = len(header) + (resource_count + 1) * 6 + alias_count * 4
    index_chunks: list[bytes] = []
    data_chunks: list[bytes] = []

    for resource_id, payload in pack.resources:
        index_chunks.append(struct.pack("<HI", resource_id, data_offset))
        data_chunks.append(payload)
        data_offset += len(payload)

    index_chunks.append(struct.pack("<HI", 0, data_offset))
    alias_chunks = [struct.pack("<HH", alias_id, target_index) for alias_id, target_index in pack.aliases]
    return b"".join([header, *index_chunks, *alias_chunks, *data_chunks])


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(data)
        temporary_path = pathlib.Path(handle.name)
    os.replace(temporary_path, path)


def patch_pak(path: pathlib.Path) -> tuple[int, int]:
    raw = path.read_bytes()
    pack = read_data_pack(raw)
    changed_resources = 0
    patched_resources: list[tuple[int, bytes]] = []

    for resource_id, payload in pack.resources:
        patched = patch_resource(payload)
        if patched != payload:
            changed_resources += 1
        patched_resources.append((resource_id, patched))

    if not changed_resources:
        return 0, 0

    rebuilt = write_data_pack(
        DataPack(pack.version, pack.encoding, patched_resources, pack.aliases)
    )
    # Parse the rebuilt pack before replacing the original so malformed output
    # cannot be shipped silently.
    read_data_pack(rebuilt)
    atomic_write(path, rebuilt)
    return changed_resources, len(raw) - len(rebuilt)


def patch_text_file(path: pathlib.Path) -> bool:
    raw = path.read_bytes()
    patched = replace_brand_bytes(raw)
    if patched == raw:
        return False
    atomic_write(path, patched)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rewrite user-visible Brave branding in Chromium .pak resources."
    )
    parser.add_argument("root", type=pathlib.Path)
    parser.add_argument(
        "--include-text",
        action="store_true",
        help="also patch selected loose text resource files",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")

    pak_files = 0
    resource_count = 0
    byte_delta = 0
    text_files = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".pak":
            try:
                changed, delta = patch_pak(path)
            except ValueError as error:
                print(f"[Haly] skipped unsupported pack {path}: {error}")
                continue
            if changed:
                pak_files += 1
                resource_count += changed
                byte_delta += delta
                print(f"[Haly] patched {changed:4d} resource(s): {path}")
        elif args.include_text and path.suffix.lower() in TEXT_SUFFIXES:
            if patch_text_file(path):
                text_files += 1
                print(f"[Haly] patched text resource: {path}")

    print(
        f"[Haly] completed: {pak_files} pack(s), {resource_count} resource(s), "
        f"{text_files} loose text file(s), size delta {byte_delta:+d} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
