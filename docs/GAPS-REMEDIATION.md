# Ten-Gap Remediation (v0.2.0)

This tracks the 10 reliability/security/release gaps closed in this update.

1. JSON5 parser safety
- Before: ad-hoc `//` stripping could corrupt strings.
- Now: proper `json5` parser with typed config validation.

2. Config migration path
- Before: only `~/.config/gram/config.json5`.
- Now: primary `~/.config/glam/config.json5` with legacy fallback.

3. Chrome profile handling
- Before: `--chrome-profile` accepted but not used for cookie DB path.
- Now: profile-specific cookie DB resolution on macOS/Linux candidates.

4. Firefox profile handling
- Before: `--firefox-profile` accepted but not used for DB path.
- Now: profile-specific `cookies.sqlite` resolution + glob fallback.

5. Browser lock handling
- Before: `--no-lock` existed but did nothing meaningful.
- Now: cookie DB copy-to-temp strategy for lock bypass.

6. Secret leakage in login output
- Before: raw credentials printed by default when not saving.
- Now: secrets are hidden by default; explicit `--print-env` required.

7. Highlight path sanitization
- Before: highlight titles used directly in filesystem paths.
- Now: titles sanitized before download target creation.

8. Exception hygiene
- Before: many broad exceptions without chaining.
- Now: explicit exception chaining and narrowed Instaloader exception paths.

9. Static quality gates
- Before: ruff/mypy failures across source.
- Now: strict typing and lint issues addressed in updated modules/tests.

10. Release scaffolding gaps
- Before: no npm package wrapper and placeholder Homebrew formula.
- Now: npm wrapper + Homebrew formula template + release checklist + SHA update script.
