#!/usr/bin/env python3
"""Check Git blobs introduced by a pull request without downloading LFS objects."""
import io
import json
import os
import re
import subprocess
import sys

MIB = 1024 * 1024
WARNING = 2 * MIB
GIT_LIMIT = 5 * MIB
LFS_LIMIT = 50 * MIB
TOTAL_WARNING = 50 * MIB
OID = re.compile(rb"[0-9a-f]{40,64}\Z")
LFS_HASH = re.compile(rb"oid sha256:[0-9a-f]{64}\Z")


def git(*args, input_data=None):
    return subprocess.run(
        ["git", *args], input=input_data, stdout=subprocess.PIPE, check=True
    ).stdout


def object_paths(base, head):
    """Include all new historical blobs and paths changed in the final tree."""
    common = git("merge-base", base, head).strip().decode("ascii")
    objects = {}
    previous = None
    for item in git("rev-list", "--objects", "-z", head, "--not", common).split(b"\0"):
        if OID.fullmatch(item):
            previous = item
            objects.setdefault(item, set())
        elif item.startswith(b"path=") and previous is not None:
            objects[previous].add(item[5:])

    # A newly added path can point to a pre-existing object in the base tree.
    current = []
    parts = git("diff", "--raw", "-z", "--no-abbrev", "--no-renames", common, head).split(b"\0")
    for index in range(0, len(parts) - 1, 2):
        fields = parts[index].split()
        if len(fields) == 5 and fields[4] != b"D" and OID.fullmatch(fields[3]):
            objects.setdefault(fields[3], set()).add(parts[index + 1])
            current.append(fields[3])
    return objects, current


def batch_info(oids):
    if not oids:
        return {}
    raw = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
              input_data=b"".join(oid + b"\n" for oid in oids))
    result = {}
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) != 3:
            raise ValueError(f"Cannot read Git object: {line!r}")
        oid, kind, size = fields
        if kind == b"blob":
            result[oid] = int(size)
    return result


def pointer_size(body):
    lines = body.splitlines()
    if not lines or lines[0] != b"version https://git-lfs.github.com/spec/v1":
        return None
    hashes = [line for line in lines if LFS_HASH.fullmatch(line)]
    sizes = [line[5:] for line in lines if line.startswith(b"size ")]
    if len(hashes) != 1 or len(sizes) != 1 or not sizes[0].isdigit():
        return None
    return int(sizes[0])


def read_small_blobs(oids):
    if not oids:
        return {}
    raw = git("cat-file", "--batch", input_data=b"".join(oid + b"\n" for oid in oids))
    stream = io.BytesIO(raw)
    result = {}
    for expected in oids:
        header = stream.readline().split()
        if len(header) != 3 or header[0] != expected or header[1] != b"blob":
            raise ValueError(f"Cannot read Git blob: {header!r}")
        length = int(header[2])
        content = stream.read(length)
        if len(content) != length or stream.read(1) != b"\n":
            raise ValueError("Incomplete Git blob response")
        result[expected] = content
    return result


def format_path(paths, oid):
    if not paths:
        return f"Git object {oid.decode('ascii')}"
    # JSON escaping keeps unusual filenames from forging GitHub workflow commands.
    return ", ".join(json.dumps(os.fsdecode(p), ensure_ascii=True) for p in sorted(paths))


def main(base, head):
    objects, current = object_paths(base, head)
    sizes = batch_info(list(objects))
    small = [oid for oid, size in sizes.items() if size <= 1024]
    pointer_sizes = {oid: pointer_size(body) for oid, body in read_small_blobs(small).items()}
    total = sum(pointer_sizes.get(oid) if pointer_sizes.get(oid) is not None else sizes[oid]
                for oid in current if oid in sizes)
    errors = []
    warnings = []
    for oid, size in sizes.items():
        actual = pointer_sizes.get(oid)
        lfs = actual is not None
        actual = actual if lfs else size
        path = format_path(objects[oid], oid)
        if lfs and actual > LFS_LIMIT:
            errors.append(f"{path}: LFS object {actual} bytes ({actual / MIB:.2f} MiB) exceeds 50 MiB; use external storage.")
        elif not lfs and actual > GIT_LIMIT:
            errors.append(f"{path}: Git blob {actual} bytes ({actual / MIB:.2f} MiB) exceeds 5 MiB; compress it, use Git LFS for appropriate binaries, or external storage.")
        elif actual > WARNING:
            warnings.append(f"{path}: {'LFS object' if lfs else 'Git blob'} is {actual / MIB:.2f} MiB; check whether it can be reduced.")
    if total > TOTAL_WARNING:
        warnings.append(f"Final added or changed files total {total / MIB:.2f} MiB, exceeding 50 MiB.")
    def annotation(message):
        return message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

    for warning in warnings:
        print(f"::warning::{annotation(warning)}")
    for error in errors:
        print(f"::error::{annotation(error)}")
    if errors:
        print("Remove oversized versions from the PR commit history as well as its final tree; rebase merges retain intermediate commits.")
    print(f"Checked {len(sizes)} unique file versions; final added or changed files total {total / MIB:.2f} MiB.")
    return bool(errors)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: check-pr-file-sizes.py BASE_SHA HEAD_SHA")
    try:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    except (ValueError, subprocess.CalledProcessError) as exc:
        sys.exit(f"File-size check failed: {exc}")
