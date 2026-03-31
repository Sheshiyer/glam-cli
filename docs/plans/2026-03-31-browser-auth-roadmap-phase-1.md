# Browser Auth Roadmap Phase 1 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the first roadmap slice for browser authentication: explicit diagnostics, structured debug metadata, typed extraction failures, and a dedicated browser-auth module that owns browser-cookie internals.

**Architecture:** Move Chrome/Firefox cookie-file resolution, copied DB preparation, keychain-cache handling, and extractor execution into `src/gram/browser_auth.py`. Keep `src/gram/auth.py` focused on application-level auth state and delegate browser extraction to the new module. Expose diagnostics through `glam login --diagnose` and structured debug output through `glam login --debug-auth`.

**Tech Stack:** Python 3.9+, Click, `browser_cookie3`, `pytest`, `ruff`

---

### Task 1: Add the failing tests first

**Files:**
- Create: `tests/test_browser_auth.py`
- Modify: `tests/test_cli_login.py`

**Step 1: Browser auth diagnosis tests**

Write failing tests for:
- missing Chrome cookie DB returns a typed error/diagnosis code
- successful Chrome extraction returns structured debug info with `key_source`
- missing Instagram cookies produces a typed missing-cookie failure

**Step 2: CLI diagnose/debug tests**

Write failing tests for:
- `glam login --chrome-profile Default --diagnose` prints diagnosis output without saving credentials
- `glam login --chrome-profile Default --debug-auth` emits structured debug fields
- login errors include the typed error code

### Task 2: Extract browser logic into a dedicated module

**Files:**
- Create: `src/gram/browser_auth.py`
- Modify: `src/gram/auth.py`

**Step 1: Create browser-auth data structures**

Add:
- `BrowserAuthDebugInfo`
- `BrowserAuthResult`
- `BrowserAuthDiagnosis`
- typed `BrowserAuthError` subclasses

**Step 2: Move browser-specific logic**

Move:
- cookie file resolution
- cookie DB copy handling
- Chrome Safe Storage cache hook
- cookie extraction and required-cookie validation

**Step 3: Delegate from `AuthManager`**

Keep the public `AuthManager.extract_from_chrome()` and `extract_from_firefox()` methods, but delegate to the new browser-auth module.

### Task 3: Add CLI diagnostics and debug output

**Files:**
- Modify: `src/gram/cli.py`
- Modify: `src/gram/output.py`

**Step 1: Add flags**

Add:
- `--diagnose`
- `--debug-auth`

to `glam login`.

**Step 2: Output diagnosis/debug data**

Expose structured output showing:
- browser
- profile
- cookie DB path
- copied DB path usage
- key source
- error code/message

### Task 4: Docs and verification

**Files:**
- Modify: `README.md`
- Modify: `docs/COOKIE-EXTRACTION.md`
- Modify: `tasks/todo.md`

**Step 1: Document the new flow**

Add examples for:
- `glam login --chrome-profile Default --diagnose`
- `glam login --chrome-profile Default --debug-auth`

**Step 2: Verify**

Run:
- `.venv/bin/ruff check src/gram/auth.py src/gram/browser_auth.py src/gram/cli.py src/gram/output.py tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py`
- `.venv/bin/pytest tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py -v`

Expected:
- lint clean
- all targeted tests pass
