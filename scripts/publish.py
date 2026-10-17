#!/usr/bin/env python3
"""Publish a prepared package using the operator's workspace .env credential."""

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid


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


def run(command, token, env, cwd=ROOT, extra_secrets=()):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    for output, stream in ((result.stdout, sys.stdout), (result.stderr, sys.stderr)):
        for secret in (token,) + tuple(extra_secrets):
            output = output.replace(secret, "<redacted>")
        stream.write(output)
    return result.returncode


def publish_npm(token, dry_run, otp_from_env=False):
    otp = credential("npm_otp") if otp_from_env else None
    with tempfile.TemporaryDirectory(prefix="verbs-npm-") as directory:
        config = Path(directory) / "npmrc"
        config.write_text('//registry.npmjs.org/:_authToken=${NODE_AUTH_TOKEN}\n')
        config.chmod(0o600)
        env = os.environ.copy()
        env.update({
            "NODE_AUTH_TOKEN": token,
            "NPM_CONFIG_USERCONFIG": str(config),
            "NPM_CONFIG_LOGS_MAX": "0",
        })
        if otp:
            env["NPM_CONFIG_OTP"] = otp
        command = ["npm", "publish", "--access", "public", "--registry", "https://registry.npmjs.org/"]
        if dry_run:
            command.append("--dry-run")
        return run(command, token, env, ROOT / "packages/js", (otp,) if otp else ())


def publish_luarocks(token, dry_run):
    # LuaRocks puts its key in the API URL. Keep this transport in-process so
    # it never becomes a curl/process argument or a lasting CLI credential.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect())
    rockspec = ROOT / "packages/lua/verbs-0.1.0-1.rockspec"

    def request(method, query=None, upload=None):
        url = "https://luarocks.org/api/1/" + urllib.parse.quote(token, safe="") + "/" + method
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"User-Agent": "verbs-publication (github.com/antimemeai/verbs)"}
        body = None
        if upload:
            boundary = "verbs-" + uuid.uuid4().hex
            body = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="rockspec_file"; '
                f'filename="{upload.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'
            ).encode() + upload.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
            headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        try:
            with opener.open(urllib.request.Request(url, data=body, headers=headers), timeout=60) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            raise SystemExit(f"LuaRocks {method} returned HTTP {error.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise SystemExit(f"LuaRocks {method} request failed; no response details logged") from None
        if result.get("two_factor_required"):
            raise SystemExit("LuaRocks requires an additional two-factor authorization")
        if result.get("errors"):
            message = str(result["errors"]).replace(token, "<redacted>")
            raise SystemExit("LuaRocks rejected " + method + ": " + message)
        return result

    status = request("check_rockspec", {"package": "verbs", "version": "0.1.0-1"})
    if status.get("version"):
        raise SystemExit("LuaRocks verbs 0.1.0-1 already exists; refusing to overwrite")
    if dry_run:
        print("LuaRocks accepted the name/version preflight; no files uploaded")
    else:
        result = request("upload", upload=rockspec)
        if result.get("is_new") and not result.get("manifests"):
            raise SystemExit("LuaRocks uploaded to a user manifest, but the root name was unavailable")
        print("LuaRocks uploaded rockspec:", str(result.get("module_url", "")).replace(token, "<redacted>"))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", choices=("crates", "pypi", "npm", "luarocks"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--otp-from-env", action="store_true",
                        help="For npm only: read a current one-time code from npm_otp in workspace .env")
    args = parser.parse_args()
    if args.otp_from_env and args.registry != "npm":
        parser.error("--otp-from-env is only supported for npm")
    token = credential(args.registry)
    if args.registry == "npm":
        return publish_npm(token, args.dry_run, args.otp_from_env)
    if args.registry == "luarocks":
        return publish_luarocks(token, args.dry_run)
    env = os.environ.copy()
    if args.registry == "crates":
        env["CARGO_REGISTRY_TOKEN"] = token
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
    return run(command, token, env)


if __name__ == "__main__":
    raise SystemExit(main())
