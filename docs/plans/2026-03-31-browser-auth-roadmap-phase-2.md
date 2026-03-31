# Browser Auth Roadmap Phase 2 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand browser login support beyond Chrome/Firefox through a generic `--browser/--profile` flow while keeping the legacy flags working.

**Architecture:** Add a shared browser registry in `src/gram/browser_auth.py` that describes supported browsers, the `browser_cookie3` extractor name, default profile, browser family, and macOS safe-storage metadata when relevant. Route CLI login through the registry using a generic browser selector, while preserving the existing `--chrome-profile` and `--firefox-profile` options as compatibility shims.

**Tech Stack:** Python 3.9+, Click, `browser_cookie3`, `pytest`, `ruff`

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `tests/test_browser_auth.py`
- Modify: `tests/test_cli_login.py`
- Modify: `tests/test_cli_exit_codes.py`

**Step 1: Browser registry dispatch tests**

Write failing tests for:
- `extract_browser(browser="brave", ...)` using the Brave extractor
- the returned debug payload naming `browser="brave"`
- unsupported browsers still failing clearly

**Step 2: CLI generic login tests**

Write failing tests for:
- `glam login --browser brave --profile Default --debug-auth`
- mixing `--browser` with `--chrome-profile` is rejected
- `glam login` with no browser selection now points users to the generic browser syntax

### Task 2: Implement a shared browser registry

**Files:**
- Modify: `src/gram/browser_auth.py`

**Step 1: Create browser specs**

Add a registry covering:
- `chrome`
- `firefox`
- `brave`
- `arc`
- `chromium`
- `edge`
- `opera`
- `opera-gx`
- `vivaldi`

**Step 2: Generalize browser extraction**

Use the registry to:
- select the extractor function dynamically
- set default profile names
- set macOS keychain service/account metadata for Chromium-family browsers when known

### Task 3: Add generic CLI browser selection

**Files:**
- Modify: `src/gram/cli.py`

**Step 1: Add generic flags**

Add:
- `--browser`
- `--profile`

**Step 2: Preserve compatibility**

Keep:
- `--chrome-profile`
- `--firefox-profile`

but route them through the same resolution path.

### Task 4: Docs and verification

**Files:**
- Modify: `README.md`
- Modify: `docs/COOKIE-EXTRACTION.md`
- Modify: `docs/API.md`
- Modify: `tasks/todo.md`

**Step 1: Document the broader browser surface**

Add examples for:
- `glam login --browser brave --profile Default --save`
- `glam login --browser arc --profile Default --diagnose`

**Step 2: Verify**

Run:
- `.venv/bin/ruff check src/gram/browser_auth.py src/gram/auth.py src/gram/cli.py tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py`
- `.venv/bin/pytest tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py -v`

Expected:
- lint clean
- all targeted tests pass
