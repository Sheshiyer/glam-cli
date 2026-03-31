# Chrome Safe Storage Cache Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reuse one successful macOS Chrome Safe Storage key lookup across repeated serial Chrome cookie extractions in the same process so the keychain prompt does not re-fire on every extraction attempt.

**Architecture:** Keep the fix inside `src/gram/auth.py` so the public CLI flow stays unchanged. Patch `browser_cookie3` at runtime on macOS by wrapping its internal `_get_osx_keychain_password` helper with a small cache keyed by `(service, user)`, then verify the wrapper only installs once and remains transparent for normal extraction behavior.

**Tech Stack:** Python 3.9+, `browser_cookie3`, `pytest`, `monkeypatch`

---

### Task 1: Capture the upstream root cause in the repo task log

**Files:**
- Modify: `tasks/todo.md`

**Step 1: Record the root cause**

Add checklist items stating that `browser_cookie3` performs `/usr/bin/security find-generic-password` during Chromium extractor construction on macOS.

**Step 2: Record the intended fix**

Document that the repo-local fix is an auth-layer cache keyed by the macOS keychain service and account name.

### Task 2: Add a cached macOS keychain lookup wrapper

**Files:**
- Modify: `src/gram/auth.py`

**Step 1: Write a helper that installs once**

Add a small helper that detects macOS, checks that `browser_cookie3` exposes `_get_osx_keychain_password`, and wraps that function once.

**Step 2: Cache by service/user pair**

Use a module-local cache so repeated serial extractions in the same Python process reuse the first successful `Chrome Safe Storage` lookup.

**Step 3: Call the helper from the Chrome extraction path**

Prime the cache wrapper immediately before calling `browser_cookie3.chrome(...)`.

### Task 3: Add regression tests

**Files:**
- Modify: `tests/test_auth_extractors.py`

**Step 1: Simulate repeated serial Chrome extractions**

Monkeypatch a fake `browser_cookie3` module with a fake `_get_osx_keychain_password` and a fake `chrome(...)` implementation that calls through the helper twice.

**Step 2: Verify only one key lookup occurs**

Assert that two `AuthManager.extract_from_chrome(...)` calls in the same process trigger exactly one underlying macOS key lookup for the same service/user pair.

**Step 3: Verify the wrapper is transparent**

Assert the extraction result still returns the expected cookies and profile-selected cookie DB behavior.

### Task 4: Verify and review

**Files:**
- Modify: `tasks/todo.md`

**Step 1: Run focused tests**

Run: `pytest tests/test_auth_extractors.py tests/test_cli_login.py -v`

Expected: all tests pass.

**Step 2: Record review notes**

Update `tasks/todo.md` with the root cause, the auth-layer cache behavior, and the exact verification command used.
