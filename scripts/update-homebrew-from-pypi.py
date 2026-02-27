#!/usr/bin/env python3
"""Update Homebrew formula URL/SHA from PyPI sdist metadata."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FORMULA = ROOT / "homebrew" / "glam-cli.rb"
PYPROJECT = ROOT / "pyproject.toml"


def load_version() -> str:
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11+ required for tomllib.")

    import tomllib

    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def fetch_pypi_sdist(package_name: str, version: str) -> tuple[str, str]:
    url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    with urlopen(url) as response:  # nosec - trusted public API endpoint
        payload = json.load(response)

    for file_info in payload.get("urls", []):
        if file_info.get("packagetype") == "sdist":
            sdist_url = str(file_info["url"])
            sha = str(file_info["digests"]["sha256"])
            return sdist_url, sha

    raise SystemExit(f"No sdist found for {package_name}=={version}")


def update_formula(url: str, sha256: str) -> None:
    content = FORMULA.read_text(encoding="utf-8")
    content, url_replacements = re.subn(
        r'^(\s*url\s+").*(")',
        rf'\1{url}\2',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    content, sha_replacements = re.subn(
        r'^(\s*sha256\s+")([0-9a-f]{64}|RELEASE_SHA256)(")',
        rf'\1{sha256}\3',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if url_replacements != 1 or sha_replacements != 1:
        raise SystemExit("Could not update formula url/sha256 lines.")

    FORMULA.write_text(content, encoding="utf-8")


def main() -> None:
    package_name = sys.argv[1] if len(sys.argv) > 1 else "glam-cli"
    version = sys.argv[2] if len(sys.argv) > 2 else load_version()

    sdist_url, sha256 = fetch_pypi_sdist(package_name, version)
    update_formula(sdist_url, sha256)

    print(f"Updated {FORMULA}")
    print(f"url: {sdist_url}")
    print(f"sha256: {sha256}")


if __name__ == "__main__":
    main()
