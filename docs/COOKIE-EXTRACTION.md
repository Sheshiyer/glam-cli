# Cookie Extraction Guide for glam-cli

`glam-cli` uses cookie-based authentication similar to bird (Twitter/X CLI).

## Required Cookies

You need these cookies from `instagram.com`:

- `sessionid`
- `csrftoken`
- `ds_user_id`

## Method 1: Browser DevTools (Manual)

1. Log into [instagram.com](https://www.instagram.com) in Chrome or Firefox.
2. Open DevTools (`F12` or `Cmd+Option+I`).
3. Go to Application/Storage -> Cookies -> `https://www.instagram.com`.
4. Copy `sessionid`, `csrftoken`, and `ds_user_id`.

Set environment variables:

```bash
export INSTAGRAM_SESSIONID="..."
export INSTAGRAM_CSRFTOKEN="..."
export INSTAGRAM_USER_ID="..."
```

## Method 2: Automated Extraction (`glam login`)

```bash
# Chrome
glam login --browser chrome --profile Default --save

# Firefox
glam login --browser firefox --profile default-release --save

# Brave
glam login --browser brave --profile Default --save

# Arc
glam login --browser arc --profile Default --save

# Use copied DB strategy if browser lock errors occur
glam login --browser chrome --profile Default --no-lock --save

# Diagnose browser cookie extraction
glam login --browser chrome --profile Default --diagnose

# Show structured auth debug details
glam login --browser chrome --profile Default --debug-auth
```

Default behavior:
- `glam login` does not print raw credentials.
- Use `--print-env` only if you intentionally need export statements printed.
- Preferred browser selection uses `--browser` plus `--profile`.
- Legacy flags `--chrome-profile` and `--firefox-profile` still work.
- On macOS, successful Chromium safe-storage lookups are cached in a glam-owned keychain entry so later CLI runs can often avoid repeating the browser prompt.

## Method 3: Config File

Create `~/.config/glam/config.json5`:

```json5
{
  sessionid: "your_sessionid_here",
  csrftoken: "your_csrftoken_here",
  userId: "your_userid_here"
}
```

Secure permissions:

```bash
chmod 600 ~/.config/glam/config.json5
```

## Troubleshooting

### Missing cookies

- Ensure you are logged into `instagram.com` in the selected browser profile.
- Try browser-specific profile names explicitly (`Default`, `Profile 1`, etc.).

### Browser lock errors

- Use `--no-lock` to read from a copied cookie DB.

### Chrome Safe Storage or profile issues

- Use `glam login --browser chrome --profile Default --diagnose` to inspect the resolved cookie DB path and the current auth error code.
- Use `glam login --browser chrome --profile Default --debug-auth` to emit structured debug fields such as `cookie_db_path`, `prepared_cookie_db_path`, and `key_source`.
- `key_source` may report `cache-hit`, `persistent-cache-hit`, `keychain`, or `fallback`.
- If a glam-managed persistent cache entry becomes stale, glam clears it and retries the extraction once before surfacing the failure.
- Supported `--browser` values include `chrome`, `firefox`, `brave`, `arc`, `chromium`, `edge`, `opera`, `opera-gx`, and `vivaldi`.

### Invalid credentials

- Cookies may be expired.
- Re-run `glam login --save` after refreshing your Instagram session.

## Security Notes

1. Cookies can fully authenticate your account.
2. Do not share terminal history or logs containing credential exports.
3. Prefer `--save` to store credentials in `~/.config/glam/config.json5` with `0600` permissions.
