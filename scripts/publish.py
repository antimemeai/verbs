#!/usr/bin/env python3
"""Publish a prepared package using the operator's workspace .env credential."""

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def credential(key):
    matches = []
    for line in (ROOT.parent / ".env").read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        name, separator, value = line.partition("=")
        if separator and name.strip() == key:
            try:
                parts = shlex.split(value, comments=True)
            except ValueError:
                raise SystemExit(f"Malformed {key} credential in workspace .env") from None
            if len(parts) != 1 or not parts[0]:
                raise SystemExit(f"Empty or malformed {key} credential in workspace .env")
            matches.append(parts[0])
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {key} credential in workspace .env")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", choices=("crates", "pypi"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    token = credential(args.registry)
    env = os.environ.copy()
    if args.registry == "crates":
        env["CARGO_REGISTRIES_CRATES_IO_TOKEN"] = token
        env["PATH"] = str(Path.home() / ".cargo/bin") + os.pathsep + env.get("PATH", "")
        command = [str(Path.home() / ".cargo/bin/cargo"), "publish", "--registry", "crates-io"]
    else:
        dist = ROOT / "packages/python/dist"
        wheels = sorted(dist.glob("pverbs-*.whl"))
        sdists = sorted(dist.glob("pverbs-*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            raise SystemExit("Build one pverbs wheel and sdist in packages/python/dist first")
        if wheels[0].name.split("-")[1] != sdists[0].name[len("pverbs-"):-len(".tar.gz")]:
            raise SystemExit("The pverbs wheel and sdist versions must match")
        env["UV_PUBLISH_TOKEN"] = token
        command = [
            "uv", "--no-config", "publish", "--trusted-publishing", "never",
            "--publish-url", "https://upload.pypi.org/legacy/",
            "--check-url", "https://pypi.org/simple/",
            str(wheels[0]), str(sdists[0]),
        ]
    if args.dry_run:
        command.append("--dry-run")
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    for output, stream in ((result.stdout, sys.stdout), (result.stderr, sys.stderr)):
        stream.write(output.replace(token, "<redacted>"))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
