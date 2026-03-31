# Release Prep v0.3.0 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare `glam-cli` for a `v0.3.0` release by updating descriptions, versioned docs, and release-facing metadata, then verify the package is internally consistent.

**Architecture:** Keep the release prep narrow: update the canonical version fields in `pyproject.toml`, `package.json`, and `src/gram/__init__.py`; refresh the README and package descriptions to reflect the browser-auth roadmap; and validate the result with lint, tests, and a local build. Do not mutate the Homebrew formula URL/sha until a real package publish exists for the new version.

**Tech Stack:** Python 3.9+, Click, `browser_cookie3`, Hatchling, npm metadata, `pytest`, `ruff`

---

### Task 1: Update release metadata

**Files:**
- Modify: `pyproject.toml`
- Modify: `package.json`
- Modify: `src/gram/__init__.py`

**Step 1: Bump the version**

Update the release version from `0.2.0` to `0.3.0` in:
- Python package metadata
- npm wrapper metadata
- runtime `__version__`

**Step 2: Refresh the descriptions**

Update the description strings to emphasize:
- browser-based login
- saved posts, stories, highlights
- multi-browser auth support

### Task 2: Refresh the README release summary

**Files:**
- Modify: `README.md`

**Step 1: Update visible release markers**

Update:
- the version badge
- the `What Changed` heading
- the release summary bullets

**Step 2: Reflect the recent browser-auth roadmap work**

Capture:
- generic multi-browser login
- diagnose/debug-auth flows
- cross-process macOS Chromium safe-storage caching

### Task 3: Verify release sanity

**Files:**
- Modify: `tasks/todo.md`

**Step 1: Run verification**

Run:
- `./.venv/bin/ruff check src/gram/browser_auth.py src/gram/auth.py src/gram/cli.py tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py`
- `./.venv/bin/pytest tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py -v`
- `./.venv/bin/python -m build`

Expected:
- lint clean
- targeted tests pass
- build completes successfully

### Task 4: Push assessment

**Files:**
- Modify: `tasks/todo.md`

**Step 1: Check repo viability**

Confirm whether:
- `01-Projects/gram-cli` is a standalone git repo
- a valid remote exists for `glam-cli`
- the current environment can push to that remote

**Step 2: Defer formula publish-only changes**

Do not update `homebrew/glam-cli.rb` versioned artifact URLs or SHAs until the new package has actually been published.
