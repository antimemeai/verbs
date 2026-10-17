#!/usr/bin/env python3
"""Extract a GitHub source ZIP into a clean reference copy.

Usage: extract-reference.py ARCHIVE DEST [PREFIX ...]
Strips the single top-level directory. Omits symlinks, .git entries,
.DS_Store and __MACOSX. If PREFIXes are given, keeps only paths under them.
Prints: files, omitted symlinks, omitted detritus, omitted by prefix.
"""
import os, stat, sys, zipfile
archive, dest, prefixes = sys.argv[1], sys.argv[2], tuple(sys.argv[3:])
files = links = detritus = filtered = 0
with zipfile.ZipFile(archive) as z:
    for info in z.infolist():
        parts = info.filename.split("/", 1)
        if len(parts) < 2 or not parts[1]:
            continue
        rel = parts[1]
        if info.is_dir():
            continue
        comps = rel.split("/")
        if any(c in (".git", "__MACOSX", ".DS_Store") for c in comps):
            detritus += 1; continue
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            links += 1; continue
        if prefixes and not any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in prefixes):
            filtered += 1; continue
        out = os.path.realpath(os.path.join(dest, rel))
        if not out.startswith(os.path.realpath(dest) + os.sep):
            raise SystemExit(f"unsafe path {rel}")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with z.open(info) as src, open(out, "wb") as dst:
            dst.write(src.read())
        os.chmod(out, 0o755 if mode & 0o111 else 0o644)
        files += 1
print(f"{files}\t{links}\t{detritus}\t{filtered}")
