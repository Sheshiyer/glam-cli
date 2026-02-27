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
glam login --chrome-profile Default --save
glam login --firefox-profile default-release --save
glam login --chrome-profile "Profile 1" --print-env
```

Notes:
- `login` no longer prints raw credential values by default.
- Use `--print-env` only when you intentionally want sensitive exports in stdout.

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
