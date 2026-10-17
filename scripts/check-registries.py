#!/usr/bin/env python3
"""Check public package endpoints; a 404 is not ownership or guaranteed availability."""

import concurrent.futures
from datetime import datetime, timezone
import urllib.error
import urllib.request


PACKAGES = (
    ("PHP", "antimemeai/verbs", "https://repo.packagist.org/p2/antimemeai/verbs.json"),
    ("Dart", "verbs", "https://pub.dev/api/packages/verbs"),
    ("Ruby", "verbs", "https://rubygems.org/api/v1/gems/verbs.json"),
    ("Ruby alternative", "verbs-agent", "https://rubygems.org/api/v1/gems/verbs-agent.json"),
    ("Erlang/Elixir", "verbs", "https://hex.pm/api/packages/verbs"),
    ("Erlang alternative", "verbs_agent", "https://hex.pm/api/packages/verbs_agent"),
    (".NET", "Verbs", "https://api.nuget.org/v3-flatcontainer/verbs/index.json"),
    ("Haskell", "verbs", "https://hackage.haskell.org/package/verbs/preferred.json"),
)


def check(package):
    ecosystem, name, url = package
    request = urllib.request.Request(url, headers={
        "User-Agent": "verbs-registry-check (https://github.com/antimemeai/verbs)"
    })
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return ecosystem, name, "request failed; availability unknown"
    if status == 200:
        result = "listed"
    elif status == 404:
        result = "not found; not reserved"
    else:
        result = f"HTTP {status}; availability unknown"
    return ecosystem, name, result


def main():
    print(datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for ecosystem, name, result in pool.map(check, PACKAGES):
            print(f"{ecosystem}\t{name}\t{result}")


if __name__ == "__main__":
    main()
