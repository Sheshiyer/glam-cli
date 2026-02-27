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
glam login --chrome-profile Default --save

# Firefox
glam login --firefox-profile default-release --save

# Use copied DB strategy if browser lock errors occur
glam login --chrome-profile Default --no-lock --save
```

Default behavior:
- `glam login` does not print raw credentials.
- Use `--print-env` only if you intentionally need export statements printed.

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

### Invalid credentials

- Cookies may be expired.
- Re-run `glam login --save` after refreshing your Instagram session.

## Security Notes

1. Cookies can fully authenticate your account.
2. Do not share terminal history or logs containing credential exports.
3. Prefer `--save` to store credentials in `~/.config/glam/config.json5` with `0600` permissions.
