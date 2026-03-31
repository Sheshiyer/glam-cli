# API Reference

`glam` is a command-line interface for downloading Instagram content with optional cookie-based authentication.

## Global Usage

```bash
glam [COMMAND] [OPTIONS]
```

Legacy alias: `gram` still works.

## Commands

### `whoami`

```bash
glam whoami
```

### `profile <user>`

```bash
glam profile username
glam profile username --limit 50 --resume -o ~/Downloads/instagram
glam profile username --json
```

### `post <url>`

```bash
glam post https://www.instagram.com/p/ABC123/
```

### `saved`

Download saved/bookmarked posts for the authenticated account.

```bash
glam saved
glam saved --limit 50 --resume
```

### `stories <user>`

```bash
glam stories username
```

### `highlights <user>`

```bash
glam highlights username
```

### `login`

```bash
glam login --browser chrome --profile Default --save
glam login --browser firefox --profile default-release --save
glam login --browser brave --profile Default --save
glam login --browser chrome --profile "Profile 1" --print-env
```

Notes:
- `login` no longer prints raw credential values by default.
- Use `--print-env` only when you intentionally want sensitive exports in stdout.
- Supported `--browser` values: `chrome`, `firefox`, `brave`, `arc`, `chromium`, `edge`, `opera`, `opera-gx`, `vivaldi`.
- Legacy `--chrome-profile` and `--firefox-profile` flags remain available.
- On macOS, successful Chromium safe-storage lookups are cached in a glam-owned keychain entry for reuse across later CLI runs.
- `--debug-auth` can report `key_source` values such as `cache-hit`, `persistent-cache-hit`, `keychain`, and `fallback`.

### `check`

```bash
glam check
```

## Authentication Sources

1. Environment variables
2. Config file at `~/.config/glam/config.json5`
3. Browser extraction via `glam login`

Legacy fallback:
- If glam config is missing, `~/.config/gram/config.json5` is read.

Required values:
- `sessionid`
- `csrftoken`
- `ds_user_id` (stored as `userId` in config)

## Exit Behavior

- Successful execution returns exit code `0`.
- Invalid input, auth failures, and download failures return non-zero exit codes.
