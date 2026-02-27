"""Configuration file management for glam CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from gram.auth import AuthCredentials

json5: Any
try:
    import json5 as _json5

    json5 = _json5
except ImportError:  # pragma: no cover - dependency is required at runtime
    json5 = None


class ConfigManager:
    """Manages glam configuration files."""

    DEFAULT_CONFIG_PATH = Path.home() / ".config" / "glam" / "config.json5"
    LEGACY_CONFIG_PATH = Path.home() / ".config" / "gram" / "config.json5"

    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = (
            Path(config_path).expanduser() if config_path else self.DEFAULT_CONFIG_PATH
        )
        self.legacy_config_path = self.LEGACY_CONFIG_PATH

    def _ensure_dir(self) -> None:
        """Ensure config directory exists."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def _resolve_read_path(self) -> Path | None:
        if self.config_path.exists():
            return self.config_path
        if self.legacy_config_path.exists():
            return self.legacy_config_path
        return None

    def load(self) -> dict[str, Any]:
        """Load config file from glam path (fallback: legacy gram path)."""
        read_path = self._resolve_read_path()
        if read_path is None:
            return {}

        try:
            content = read_path.read_text(encoding="utf-8")
            parsed = self._parse_json5(content)
            if not isinstance(parsed, dict):
                raise RuntimeError(
                    f"Config root must be an object, found {type(parsed).__name__} in {read_path}"
                )
            return dict(parsed)
        except RuntimeError:
            raise
        except Exception as err:
            raise RuntimeError(f"Failed to load config from {read_path}: {err}") from err

    def save(self, config: dict[str, Any]) -> None:
        """Save config to glam config path."""
        self._ensure_dir()

        try:
            self.config_path.write_text(
                json.dumps(config, indent=2),
                encoding="utf-8",
            )
            os.chmod(self.config_path, 0o600)
        except Exception as err:
            raise RuntimeError(f"Failed to save config to {self.config_path}: {err}") from err

    def load_auth(self) -> AuthCredentials | None:
        """Load auth credentials from config."""
        config = self.load()

        if not config:
            return None

        if "sessionid" in config and "csrftoken" in config:
            return AuthCredentials.from_dict(config)

        auth_config = config.get("auth")
        if isinstance(auth_config, dict):
            return AuthCredentials.from_dict(auth_config)

        return None

    def save_auth(self, credentials: AuthCredentials) -> None:
        """Save auth credentials to config."""
        config = self.load()
        config.update(credentials.to_dict())
        self.save(config)

    def get_download_dir(self) -> Path:
        """Get configured download directory."""
        config = self.load()
        download_dir = config.get("downloadDir")
        if isinstance(download_dir, str) and download_dir.strip():
            return Path(download_dir).expanduser()
        return Path("~/Downloads/instagram").expanduser()

    def get_chrome_profile(self) -> str:
        """Get configured Chrome profile."""
        config = self.load()
        profile = config.get("chromeProfile")
        if isinstance(profile, str) and profile.strip():
            return profile
        return "Default"

    def get_firefox_profile(self) -> str:
        """Get configured Firefox profile."""
        config = self.load()
        profile = config.get("firefoxProfile")
        if isinstance(profile, str) and profile.strip():
            return profile
        return "default-release"

    @staticmethod
    def _parse_json5(content: str) -> dict[str, Any]:
        if json5 is not None:
            parsed = json5.loads(content)
            if isinstance(parsed, dict):
                return dict(parsed)
            raise RuntimeError("Config file must contain a JSON object")

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return dict(parsed)
            raise RuntimeError("Config file must contain a JSON object")
        except json.JSONDecodeError as err:
            raise RuntimeError(
                "Config uses JSON5 features but json5 dependency is missing. "
                "Install with: pip install json5"
            ) from err
