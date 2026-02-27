#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORMULA="$ROOT_DIR/homebrew/glam-cli.rb"
VERSION="${1:-}"

if [[ -z "$VERSION" ]]; then
  VERSION="$(python3 - <<'PY'
from pathlib import Path
import tomllib
pyproject = Path('pyproject.toml').read_bytes()
print(tomllib.loads(pyproject.decode())['project']['version'])
PY
)"
fi

SDIST="$ROOT_DIR/dist/glam_cli-${VERSION}.tar.gz"
if [[ ! -f "$SDIST" ]]; then
  echo "Missing sdist: $SDIST"
  echo "Run: python3 -m build"
  exit 1
fi

SHA="$(shasum -a 256 "$SDIST" | awk '{print $1}')"

python3 - <<PY
from pathlib import Path
import re
formula = Path(r"$FORMULA")
content = formula.read_text(encoding="utf-8")
content, count = re.subn(
    r'^(\\s*sha256\\s+\")([0-9a-f]{64}|RELEASE_SHA256)(\")',
    rf'\\1$SHA\\3',
    content,
    count=1,
    flags=re.MULTILINE,
)
if count != 1:
    raise SystemExit("Could not find formula sha256 line to update.")
formula.write_text(content, encoding="utf-8")
print("Updated", formula)
print("sha256", "$SHA")
PY
