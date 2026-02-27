# glam-cli

[![Version](https://img.shields.io/badge/version-0.2.0-blue)](https://github.com/Sheshiyer/glam-cli)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

`glam-cli` is an Instagram command-line tool inspired by [bird](https://bird.fast/). It downloads posts, stories, and highlights using cookie-based authentication.

## What Changed (v0.2.0)

1. Rebrand to `glam-cli` with primary command `glam`.
2. Backward-compatible alias `gram` remains available.
3. Safer login output (no raw secrets unless `--print-env` is explicit).
4. Real JSON5 config parsing (`json5` dependency).
5. Legacy config fallback from `~/.config/gram/config.json5`.
6. Chrome/Firefox profile cookie path handling now actually used.
7. `--no-lock` cookie extraction mode now works through copied DB files.
8. Highlight titles are sanitized before writing paths.
9. Resume/download reliability tests expanded.
10. Release scaffolding added for npm + Homebrew + GitHub.

Detailed gap log: [`docs/GAPS-REMEDIATION.md`](docs/GAPS-REMEDIATION.md)

## Installation

### Homebrew (Release Tap)

```bash
brew tap Sheshiyer/glam
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
glam login --chrome-profile Default --save

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
3. Browser extraction: `glam login --chrome-profile ...` or `glam login --firefox-profile ...`

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

# Safer cookie extraction (no secret print by default)
glam login --chrome-profile Default

# Explicitly print shell exports (sensitive)
glam login --chrome-profile Default --print-env
```

## Command List

| Command | Description | Auth Required |
|---|---|---|
| `whoami` | Show logged-in account info | No |
| `profile <user>` | Download profile posts and metadata | No (public) |
| `post <url>` | Download single post | No (public) |
| `stories <user>` | Download current stories | Yes |
| `highlights <user>` | Download profile highlights | Yes |
| `login` | Extract cookies from browser | No |
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
