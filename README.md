# glam-cli

[![Version](https://img.shields.io/badge/version-0.3.0-blue)](https://github.com/Sheshiyer/glam-cli)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

`glam-cli` is an Instagram command-line tool inspired by [bird](https://bird.fast/). It downloads profiles, saved/bookmarked posts, stories, and highlights using browser-based cookie authentication.

## What Changed (v0.3.0)

1. Generic `glam login --browser ... --profile ...` support now covers Chrome, Firefox, Brave, Arc, Chromium, Edge, Opera, Opera GX, and Vivaldi.
2. `glam login --diagnose` and `--debug-auth` now expose typed browser-auth failures and structured debug payloads.
3. macOS Chromium safe-storage lookups now reuse a glam-owned keychain cache across CLI runs and automatically retry once after clearing stale cached secrets.
4. Legacy `--chrome-profile` and `--firefox-profile` flags remain available as compatibility shims.
5. Safer login output, copied-cookie-db `--no-lock` mode, and config fallback behavior remain in place.

Detailed gap log: [`docs/GAPS-REMEDIATION.md`](docs/GAPS-REMEDIATION.md)

## Installation

### Homebrew (Release Tap)

```bash
brew tap twc-vault/glam
brew install glam-cli
```

Formula source in this repo: `homebrew/glam-cli.rb`.

### npm (Node Wrapper)

```bash
npm install -g glam-cli
```

This installs a thin Node wrapper that runs the Python CLI (`python -m gram`). Python 3.9+ must be installed.

### From Source

```bash
git clone https://github.com/Sheshiyer/glam-cli.git
cd glam-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

```bash
# 1. Extract and save cookies from a browser profile
glam login --browser chrome --profile Default --save

# 2. Verify authentication
glam whoami

# 3. Download a profile
glam profile username

# 4. Download a specific post
glam post https://www.instagram.com/p/ABC123/
```

## Authentication

`glam` supports:

1. Environment variables (`INSTAGRAM_SESSIONID`, `INSTAGRAM_CSRFTOKEN`, `INSTAGRAM_USER_ID`)
2. Config file: `~/.config/glam/config.json5`
3. Browser extraction: `glam login --browser ... --profile ...`

Compatibility behavior:
- If `~/.config/glam/config.json5` does not exist, glam reads legacy `~/.config/gram/config.json5`.
- `glam login --save` always writes to `~/.config/glam/config.json5`.

Detailed guide: [`docs/COOKIE-EXTRACTION.md`](docs/COOKIE-EXTRACTION.md)

## Usage

```bash
# Account info
glam whoami

# Profile download
glam profile username --limit 50 --resume

# Single post
glam post https://www.instagram.com/p/ABC123/

# Stories/highlights (auth required)
glam stories username
glam highlights username

# Saved/bookmarked posts from your account
glam saved --limit 50 --resume

# Safer cookie extraction (no secret print by default)
glam login --browser chrome --profile Default

# Diagnose browser cookie extraction
glam login --browser chrome --profile Default --diagnose

# Emit structured auth debug details
glam login --browser chrome --profile Default --debug-auth

# Explicitly print shell exports (sensitive)
glam login --browser chrome --profile Default --print-env
```

Supported browser values:
- `chrome`
- `firefox`
- `brave`
- `arc`
- `chromium`
- `edge`
- `opera`
- `opera-gx`
- `vivaldi`

Legacy compatibility:
- `--chrome-profile`
- `--firefox-profile`

macOS Chromium note:
- Successful safe-storage lookups are cached in a glam-owned keychain entry so later `glam login` runs can often reuse the decrypted browser key without re-prompting.
- `--debug-auth` may report `key_source` values such as `cache-hit`, `persistent-cache-hit`, `keychain`, or `fallback`.

## Command List

| Command | Description | Auth Required |
|---|---|---|
| `whoami` | Show logged-in account info | No |
| `profile <user>` | Download profile posts and metadata | No (public) |
| `post <url>` | Download single post | No (public) |
| `saved` | Download saved/bookmarked posts from your account | Yes |
| `stories <user>` | Download current stories | Yes |
| `highlights <user>` | Download profile highlights | Yes |
| `login` | Extract cookies from a supported browser profile | No |
| `check` | Verify credentials | No |

## Development

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Quality gates
ruff check src tests
mypy src
pytest

# Build
python3 -m build
```

## Release Workflow

Use [`docs/RELEASE.md`](docs/RELEASE.md) for complete commands covering:

1. version bump
2. tests/lint/type checks
3. Python package build/upload
4. npm publish
5. Homebrew formula SHA updates
6. GitHub tag/release

GitHub migration/setup checklist: [`docs/GITHUB-SETUP.md`](docs/GITHUB-SETUP.md)

## Project Structure

```text
glam-cli/
├── README.md
├── pyproject.toml
├── package.json
├── src/gram/
├── tests/
├── docs/
│   ├── API.md
│   ├── COOKIE-EXTRACTION.md
│   └── RELEASE.md
├── scripts/
├── bin/
└── homebrew/
    └── glam-cli.rb
```

## License

MIT License. See `LICENSE`.
