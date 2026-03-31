# Browser Auth Roadmap Phase 3 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reuse successful Chromium safe-storage lookups across separate `glam` runs while recovering automatically from stale cached secrets.

**Architecture:** Extend `src/gram/browser_auth.py` with a glam-owned persistent cache backed by the macOS keychain and keep the existing in-memory cache as the first layer. Chromium extraction should record whether a key came from process cache, persistent cache, the browser keychain lookup, or the default fallback, and retry once after clearing stale cached entries when a cached secret causes extraction failure.

**Tech Stack:** Python 3.9+, Click, `browser_cookie3`, macOS `security` CLI, `pytest`, `ruff`

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `tests/test_browser_auth.py`

**Step 1: Persistent cache hit test**

Write a failing test that:
- seeds a glam-owned persistent cache hit for `("Chrome Safe Storage", "Chrome")`
- verifies the original `browser_cookie3._get_osx_keychain_password` is not called
- verifies Chrome extraction succeeds
- verifies `debug.key_source == "persistent-cache-hit"`

**Step 2: Stale cache retry test**

Write a failing test that:
- starts with a persistent cached secret for `("Chrome Safe Storage", "Chrome")`
- simulates one failed extraction using the stale cached secret
- verifies the stale persistent entry is cleared
- verifies extraction retries once and succeeds using the original browser keychain getter
- verifies `debug.key_source == "keychain"` after the successful retry

### Task 2: Implement persistent cache helpers

**Files:**
- Modify: `src/gram/browser_auth.py`

**Step 1: Add persistent-cache helpers**

Add helpers to:
- encode/decode byte secrets safely for keychain storage
- read a glam-owned cache entry from macOS keychain
- write a glam-owned cache entry to macOS keychain
- clear a glam-owned cache entry

Use a dedicated service name so glam-managed entries do not collide with the browser-owned safe-storage entries.

**Step 2: Extend key-source tracking**

Track:
- `cache-hit`
- `persistent-cache-hit`
- `keychain`
- `fallback`

and preserve `not-applicable` for non-Chromium flows.

### Task 3: Add stale-cache retry behavior

**Files:**
- Modify: `src/gram/browser_auth.py`

**Step 1: Retry once when cached secrets fail**

If Chromium extraction fails after using a process or persistent cached secret:
- clear the process cache for that `(service, account)` pair
- clear the glam-owned persistent cache entry for that pair
- retry extraction once

**Step 2: Keep fallback behavior safe**

Do not persist or process-cache `browser_cookie3.CHROMIUM_DEFAULT_PASSWORD`.

### Task 4: Docs and verification

**Files:**
- Modify: `README.md`
- Modify: `docs/COOKIE-EXTRACTION.md`
- Modify: `tasks/todo.md`

**Step 1: Document the new behavior**

Add notes explaining:
- repeated prompts are reduced across separate CLI runs on macOS
- the persistent cache is stored in a glam-owned keychain entry
- stale cached entries are invalidated and retried automatically once
- `key_source` may now report `persistent-cache-hit`

**Step 2: Verify**

Run:
- `.venv/bin/ruff check src/gram/browser_auth.py src/gram/auth.py src/gram/cli.py tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py`
- `.venv/bin/pytest tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py -v`

Expected:
- lint clean
- all targeted tests pass
