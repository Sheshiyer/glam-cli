---
name: glam-cli
description: Instagram CLI tool for downloading posts, stories, and profiles with cookie-based auth. Use when users need command-line Instagram downloads. Commands: glam profile, glam post, glam stories, glam highlights, glam whoami, glam login.
---

# glam-cli

`glam-cli` is an Instagram CLI inspired by bird (Twitter/X CLI).

## Install

```bash
# Python
pip install glam-cli

# npm wrapper
npm install -g glam-cli

# Homebrew
brew tap twc-vault/glam
brew install glam-cli
```

## Authentication

```bash
# Browser extraction + save
glam login --chrome-profile Default --save

# Optional explicit secret print
glam login --chrome-profile Default --print-env
```

Config file path: `~/.config/glam/config.json5`
Legacy fallback: `~/.config/gram/config.json5`

## Usage

```bash
glam whoami
glam profile username --limit 50 --resume
glam post https://www.instagram.com/p/ABC123/
glam stories username
glam highlights username
glam check
```

## Notes

- Primary command is `glam`.
- Backward-compatible alias `gram` is still available.
- See `docs/COOKIE-EXTRACTION.md` for cookie details.
- See `docs/RELEASE.md` for release workflow.
