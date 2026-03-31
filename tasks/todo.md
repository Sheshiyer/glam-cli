# Saved Video Processing Tasks

## In Progress: Release Prep v0.3.0

- [x] Confirm the release target and inspect repo/remotes before attempting a push.
- [x] Write the implementation plan artifact for version bump, description refresh, and README release notes.
- [x] Update package descriptions and version fields for the next release.
- [x] Refresh the README release summary to reflect the browser-auth roadmap work.
- [x] Run focused verification for lint, tests, and package build sanity.
- [x] Push if a valid standalone remote exists, otherwise record the concrete push blocker.

### Notes

- `01-Projects/gram-cli` is ignored by the vault repo and is not currently its own git repo, so pushing may require separate repo setup beyond the file changes themselves.
- The most defensible release bump for the browser-auth roadmap work is a minor release: `0.2.0` -> `0.3.0`.

### Review

- Bumped the release version to `0.3.0` in:
  - `pyproject.toml`
  - `package.json`
  - `src/gram/__init__.py`
- Refreshed release-facing descriptions in:
  - `pyproject.toml`
  - `package.json`
  - `src/gram/__init__.py`
  - `homebrew/glam-cli.rb` desc
- Updated `README.md` to:
  - move the visible release marker to `v0.3.0`
  - rewrite the `What Changed` section around the browser-auth roadmap
  - keep the current browser-auth docs/examples intact
- Tightened npm packaging so the wrapper tarball only includes the install script instead of the full `scripts/` tree with cached bytecode.
- Added a local standalone git repo for `01-Projects/gram-cli`, created commit `release: prepare v0.3.0`, and tagged `v0.3.0`.
- Push blocker recorded:
  - package metadata points at `twc-vault/glam-cli`
  - `gh repo view twc-vault/glam-cli` fails because that owner/repo does not exist
  - no remote is configured in the new local repo
- Verification:
  - `./.venv/bin/ruff check src/gram/browser_auth.py src/gram/auth.py src/gram/cli.py tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py`
  - `./.venv/bin/pytest tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py -v`
  - `./.venv/bin/python -m build`
  - `./.venv/bin/python -m twine check dist/*`
  - `npm pack --dry-run`

## In Progress: Browser Auth Roadmap Phase 3

- [x] Review the existing Chromium keychain cache and choose the persistent-cache design.
- [x] Write the implementation plan artifact for cross-process cache reuse and stale-cache retry behavior.
- [x] Add failing tests for persistent-cache hits and stale-cache invalidation.
- [x] Implement a glam-owned macOS keychain cache for Chromium safe-storage secrets.
- [x] Retry Chromium extraction once after clearing stale cached secrets.
- [x] Update docs and debug-field expectations for the new cache source.
- [x] Run focused verification and record results in review notes.

### Notes

- This phase should reduce repeated macOS prompts across separate `glam` runs, not just within one Python process.
- The cache must stay secure. Use the macOS keychain for persistence rather than writing decrypted browser secrets to disk.
- The retry logic should only clear cached state for the exact `(service, account)` pair that failed, then re-run extraction once before surfacing the error.

### Review

- Added a glam-owned macOS keychain cache layer in `src/gram/browser_auth.py` using the `security` CLI and base64-encoded secret storage.
- Kept the existing process-local cache as the first lookup layer and added explicit key-source tracking for:
  - `cache-hit`
  - `persistent-cache-hit`
  - `keychain`
  - `fallback`
- Added a one-time Chromium retry path that clears both process-local and glam-owned persistent cached secrets when a cached secret causes extraction failure.
- Added regression tests for:
  - cross-process persistent cache hits
  - stale persistent cache invalidation plus retry
  - deterministic disabling of persistent cache in process-cache-only tests
- Updated docs:
  - `README.md`
  - `docs/COOKIE-EXTRACTION.md`
  - `docs/API.md`
- Verification:
  - `.venv/bin/ruff check src/gram/browser_auth.py src/gram/auth.py src/gram/cli.py tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py`
  - `.venv/bin/pytest tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py -v`

## In Progress: Browser Auth Roadmap Phase 2

- [x] Review the post-phase-1 browser auth surface and choose the next roadmap slice.
- [x] Write the implementation plan artifact for generic browser selection and expanded Chromium-family support.
- [x] Add failing tests for `--browser/--profile` login flow and non-Chrome browser dispatch.
- [x] Implement a shared browser registry in `src/gram/browser_auth.py`.
- [x] Add support for additional browsers such as Brave, Arc, Chromium, Edge, Opera, Opera GX, and Vivaldi.
- [x] Preserve backward compatibility for `--chrome-profile` and `--firefox-profile`.
- [x] Update docs and exit-message expectations for the broader login surface.
- [x] Run focused verification and record results in review notes.

### Notes

- This phase broadens the browser-auth surface without changing the app-level auth model. The main change is that browser selection is now a registry problem instead of a growing chain of CLI conditionals.
- The new preferred CLI surface is `glam login --browser <name> --profile <profile>`, while `--chrome-profile` and `--firefox-profile` remain as compatibility shims.
- Targeted exit-code tests now explicitly neutralize config-backed auth so they do not depend on the operator's local machine state.

### Review

- Added a shared browser registry in `src/gram/browser_auth.py` covering:
  - `chrome`
  - `firefox`
  - `brave`
  - `arc`
  - `chromium`
  - `edge`
  - `opera`
  - `opera-gx`
  - `vivaldi`
- Generalized `extract_browser()` to dispatch via the registry and added `resolve_browser_profile()` for default-profile handling.
- Added generic CLI browser selection in `src/gram/cli.py`:
  - `--browser`
  - `--profile`
  - clear rejection when mixed with legacy browser flags
- Preserved backward compatibility for:
  - `--chrome-profile`
  - `--firefox-profile`
- Updated docs:
  - `README.md`
  - `docs/COOKIE-EXTRACTION.md`
  - `docs/API.md`
- Added/updated tests:
  - `tests/test_browser_auth.py`
  - `tests/test_cli_login.py`
  - `tests/test_cli_exit_codes.py`
- Verification:
  - `.venv/bin/ruff check src/gram/browser_auth.py src/gram/auth.py src/gram/cli.py tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py`
  - `.venv/bin/pytest tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py tests/test_cli_exit_codes.py -v`

## In Progress: Browser Auth Roadmap Phase 1

- [x] Review the current auth/login flow and choose the first implementation slice from the roadmap.
- [x] Write the implementation plan artifact for diagnostics, explicit auth errors, structured debug signals, and browser-auth module extraction.
- [x] Add failing tests for browser-auth diagnostics and login debug/diagnose behavior.
- [x] Extract browser-specific cookie logic out of `src/gram/auth.py` into a dedicated module.
- [x] Add explicit browser auth error codes and structured debug metadata.
- [x] Add `glam login --diagnose` and `--debug-auth` support.
- [x] Update docs for the new auth diagnostics flow.
- [x] Run focused verification and record results in review notes.

### Notes

- This phase implements the roadmap slice with the highest immediate value: better diagnosis, structured debug output, and a cleaner separation between application auth state and browser-cookie extraction internals.
- The low-level browser logic now lives in `src/gram/browser_auth.py`; `src/gram/auth.py` now delegates instead of owning Chrome/Firefox path resolution and safe-storage internals directly.
- `glam login --diagnose` is intended for root-cause analysis, while `glam login --debug-auth` is intended for successful or failing extraction runs where you want the structured debug payload.

### Review

- Added `src/gram/browser_auth.py` with:
  - browser-specific extraction functions
  - typed browser auth errors
  - structured debug metadata
  - diagnosis payloads
  - existing Chrome Safe Storage cache behavior
- Refactored `src/gram/auth.py` to:
  - keep app-level auth state
  - delegate browser extraction/diagnosis
  - expose `extract_browser_login()` and `diagnose_browser_login()`
- Updated `src/gram/cli.py` to support:
  - `glam login --diagnose`
  - `glam login --debug-auth`
  - better error formatting with explicit error codes
- Fixed `src/gram/output.py` so structured data actually prints in rich-console mode.
- Added/updated tests:
  - `tests/test_browser_auth.py`
  - `tests/test_auth_extractors.py`
  - `tests/test_cli_login.py`
- Updated docs:
  - `README.md`
  - `docs/COOKIE-EXTRACTION.md`
- Verification:
  - `.venv/bin/ruff check src/gram/auth.py src/gram/browser_auth.py src/gram/cli.py src/gram/output.py tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py`
  - `.venv/bin/pytest tests/test_browser_auth.py tests/test_auth_extractors.py tests/test_cli_login.py -v`

## In Progress: De-duplicate Chrome Safe Storage Key Retrieval

- [x] Inspect the Chrome cookie extraction path in `src/gram/auth.py` and confirm where repeated secure-key lookups originate.
- [x] Inspect upstream `browser_cookie3` behavior for macOS keychain access and confirm whether the repeated prompt is happening inside our wrapper or the dependency.
- [x] Write a minimal plan artifact for the fix and keep the task checklist in sync.
- [x] Add a repo-local auth-layer fix so repeated serial Chrome extractions reuse one successful `Chrome Safe Storage` lookup per process.
- [x] Add regression tests proving repeated Chrome extractions do not re-run the macOS key lookup for the same service/user pair.
- [x] Run focused verification for auth extraction tests and record the result in review notes.

### Notes

- Root cause: `AuthManager.extract_from_chrome()` only called `browser_cookie3.chrome(...)` once per extraction, but upstream `browser_cookie3` re-ran `/usr/bin/security find-generic-password -s "Chrome Safe Storage" -a "Chrome"` every time a Chromium extractor was constructed on macOS.
- Desired behavior: cache a successful Chrome Safe Storage lookup once per `(service, user)` pair for the current Python process, while still allowing retries when upstream falls back to the default password (`b"peanuts"`).

### Review

- Added a repo-local macOS keychain cache wrapper in `src/gram/auth.py` that patches `browser_cookie3._get_osx_keychain_password` once and reuses successful results across repeated serial Chrome extractions.
- Added regression tests in `tests/test_auth_extractors.py` for both success caching and non-caching fallback behavior.
- Verification:
  - `.venv/bin/ruff check src/gram/auth.py tests/test_auth_extractors.py`
  - `.venv/bin/pytest tests/test_auth_extractors.py tests/test_cli_login.py -v`

## Completed: Sort Existing Saved Videos Before Processing

- [x] Inspect `/Users/sheshnarayaniyer/Downloads/instagram/saved` and confirm how videos should be ordered.
- [x] Confirm whether the repo already has local saved-video sorting or processing helpers to reuse.
- [x] Add a minimal local staging script that selects the newest saved videos without re-downloading or moving originals.
- [x] Run the staging script against the saved folder and verify the ordered result.
- [x] Record the exact staged output path and the next processing-ready inputs.

## In Progress: Extract Frames, Merge Metadata, and Integrate into Vault

- [x] Inspect the target vault resources path and correct it from `03_Resources` to `/Volumes/madara/2026/twc-vault/03-Resources`.
- [x] Inspect local vault skills under `/Volumes/madara/2026/twc-vault/.claude/skills` for checklist relevance.
- [x] Add a deterministic batch processor for frame extraction plus merged metadata JSON.
- [x] Run full-frame extraction on `/Users/sheshnarayaniyer/Downloads/instagram/saved_processing/latest_20_videos`.
- [x] Verify frame counts and merged manifest outputs.
- [x] Write a synthesis note into `/Volumes/madara/2026/twc-vault/03-Resources/Media/Video-Analysis/Instagram-Saved-Latest-20`.
- [x] Create a skills-based checklist note in the same vault folder.

## In Progress: OCR Enrichment on Selected High-Signal Frames

- [x] Confirm local OCR tooling is available.
- [x] Add a deterministic OCR enrichment script for sampled high-signal frames.
- [x] Run OCR enrichment on the extracted frame set.
- [x] Fold OCR results into the analysis manifest and per-video merged JSON files.
- [x] Update the vault synthesis note and checklist to reflect OCR completion.

## In Progress: Skill Workflow From Reel Learnings

- [x] Extract the specific reel's caption and OCR evidence.
- [x] Review skill-authoring guidance and existing skill naming/structure patterns.
- [x] Design a reusable workflow skill around the reel's actual recommended tool sequence.
- [x] Create the skill files and supporting workflow/reference docs.
- [x] Write a companion note linking the reel evidence to the created skill.
- [x] Verify the created skill paths and summarize the extracted learnings.

## In Progress: Rewrite SearchIntentAutomation for Playwright MCP + Python CLI

- [x] Inspect the created skill and identify all places where `Make.com` still appears as the active implementation.
- [x] Rewrite the execution path to use `Playwright MCP` for capture and a Python CLI for deterministic downstream orchestration.
- [x] Add resumable checkpoint behavior with taxonomy, two recommended options, and one custom direction branch.
- [x] Verify the Python CLI with blocked and resumed sample runs.
- [x] Update the companion note and task review with the rewritten execution model.

## In Progress: Extract SearchIntentAutomation into a Standalone GitHub Project

- [x] Inspect the current vault/git layout and choose the safest standalone project path.
- [x] Create a new project folder under `/Volumes/madara/2026/twc-vault/01-Projects`.
- [x] Copy the SearchIntentAutomation skill assets into the standalone folder with minimal project scaffolding.
- [x] Initialize the new folder as its own git repository and create a GitHub repo for it.
- [x] Verify the local/remote setup and record the resulting paths.

## In Progress: OCR Enrichment on High-Signal Frames

- [x] Inspect the local OCR toolchain and confirm the simplest reliable batch path.
- [ ] Add a deterministic OCR enrichment script over sampled frames.
- [ ] Run OCR enrichment on selected high-signal frames and verify output counts.
- [ ] Fold OCR results back into the analysis manifest JSON.
- [ ] Update the vault synthesis note and checklist with OCR status.

## Notes

- The saved folder is flat and uses timestamp-prefixed filenames like `YYYY-MM-DD_HH-MM-SS_shortcode.mp4`.
- Reverse lexical sort on the filename is the correct newest-to-oldest order.
- Originals in `/Users/sheshnarayaniyer/Downloads/instagram/saved` remain untouched.
- The staging layer uses symlinks and a manifest to avoid duplicating large media files.
- The analysis output uses all-frame extraction, not a sampled frame subset.
- OCR enrichment will use sampled frames for selection, then rank those samples by extracted text signal rather than attempting OCR across all 27,894 frames.

## Review

- Added `scripts/sort_saved_videos.py` to stage the newest local saved videos using symlinks plus a manifest.
- Added `scripts/extract_saved_video_frames_manifest.py` to extract every frame, capture `ffprobe`, merge sidecars, and build a final batch manifest.
- Added `scripts/enrich_saved_video_manifest_with_ocr.py` to sample frames, OCR high-signal text, and fold OCR summaries back into the manifest.
- Verified full-frame extraction output:
  - 20 videos processed
  - 27,894 frames extracted
  - 20 per-video merged JSON files
  - 20 raw `ffprobe` JSON files
  - Final manifest at `/Users/sheshnarayaniyer/Downloads/instagram/saved_processing/latest_20_videos_analysis/instagram_saved_latest_20_manifest.json`
- Verified OCR enrichment output:
  - 480 sampled frames across the batch
  - 99 retained OCR-rich frames
  - 20 per-video OCR JSON files
  - OCR data folded into the batch manifest and per-video merged JSON files
  - Canonical OCR keys normalized to `summary.ocr` and `videos[].ocr_summary`
- Wrote vault artifacts:
  - `/Volumes/madara/2026/twc-vault/03-Resources/Media/Video-Analysis/Instagram-Saved-Latest-20/Instagram-Saved-Latest-20-Video-Analysis-2026-03-07.md`
  - `/Volumes/madara/2026/twc-vault/03-Resources/Media/Video-Analysis/Instagram-Saved-Latest-20/Instagram-Saved-Latest-20-Processing-Checklist-2026-03-07.md`
  - `/Volumes/madara/2026/twc-vault/03-Resources/Media/Video-Analysis/Instagram-Saved-Latest-20/instagram-saved-latest-20-video-analysis-2026-03-07.json`
- Created reusable skill from reel learnings:
  - `/Users/sheshnarayaniyer/.claude/skills/SearchIntentAutomation/SKILL.md`
  - `/Users/sheshnarayaniyer/.claude/skills/SearchIntentAutomation/ReelEvidence.md`
  - `/Users/sheshnarayaniyer/.claude/skills/SearchIntentAutomation/Workflows/BuildOpportunityMap.md`
  - `/Users/sheshnarayaniyer/.claude/skills/SearchIntentAutomation/Workflows/ExtractFromSource.md`
- Wrote companion source note:
  - `/Volumes/madara/2026/twc-vault/03-Resources/Media/Video-Analysis/Instagram-Saved-Latest-20/DVgi0rbAWXN-SearchIntentAutomation-Workflow-2026-03-07.md`
- Rewrote the execution layer for coding agents:
  - `Make.com` remains documented only as source evidence from the reel
  - `Playwright MCP` now owns browser capture
  - `/Users/sheshnarayaniyer/.claude/skills/SearchIntentAutomation/Tools/OpportunityPipeline.py` now owns deterministic merge, resume, and checkpoint handling
  - `/Users/sheshnarayaniyer/.claude/skills/SearchIntentAutomation/Tools/CaptureStatusContract.md` now defines the Playwright-to-Python handoff contract
- Verified the rewritten pipeline:
  - `python3 -m py_compile /Users/sheshnarayaniyer/.claude/skills/SearchIntentAutomation/Tools/OpportunityPipeline.py`
  - blocked run emitted `taxonomy: auth-expired` plus the exact three decision branches
  - resumed run from `checkpoint.json` with `--direction recommended-2` produced a partial opportunity map with the blocked source deferred
  - direct success run with `capture-status.json` and two valid artifacts produced `status: ok`
- Extracted the workflow into a standalone project:
  - local project root: `/Volumes/madara/2026/twc-vault/01-Projects/search-intent-automation`
  - private GitHub repo: `https://github.com/Sheshiyer/search-intent-automation`
  - default branch: `main`
  - origin remote: `https://github.com/Sheshiyer/search-intent-automation.git`
  - initial commit pushed: `feat: initialize search intent automation project`
