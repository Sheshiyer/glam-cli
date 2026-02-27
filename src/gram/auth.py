"""Authentication management for glam CLI."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import instaloader

browser_cookie3: Any
try:
    import browser_cookie3 as _browser_cookie3  # type: ignore[import-untyped]

    browser_cookie3 = _browser_cookie3
except ImportError:
    browser_cookie3 = None

COOKIE_DOMAIN = "instagram.com"


@dataclass
class AuthCredentials:
    """Instagram authentication credentials."""

    sessionid: str
    csrftoken: str
    user_id: str

    def is_valid(self) -> bool:
        """Check if all required fields are present."""
        return bool(self.sessionid and self.csrftoken and self.user_id)

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for config storage."""
        return {
            "sessionid": self.sessionid,
            "csrftoken": self.csrftoken,
            "userId": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthCredentials:
        """Create from dictionary (handles both userId and user_id keys)."""
        return cls(
            sessionid=_coerce_string(data.get("sessionid")),
            csrftoken=_coerce_string(data.get("csrftoken")),
            user_id=_coerce_string(data.get("userId") or data.get("user_id")),
        )


class AuthManager:
    """Manages Instagram authentication."""

    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = config_path
        self._credentials: AuthCredentials | None = None
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load credentials from env vars or config file."""
        sessionid = os.getenv("INSTAGRAM_SESSIONID")
        csrftoken = os.getenv("INSTAGRAM_CSRFTOKEN")
        user_id = os.getenv("INSTAGRAM_USER_ID") or os.getenv("INSTAGRAM_DS_USER_ID")

        if sessionid and csrftoken and user_id:
            self._credentials = AuthCredentials(
                sessionid=sessionid,
                csrftoken=csrftoken,
                user_id=user_id,
            )
            return

        from gram.config import ConfigManager

        config = ConfigManager(self.config_path)
        creds = config.load_auth()
        if creds:
            self._credentials = creds

    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        return self._credentials is not None and self._credentials.is_valid()

    def get_credentials(self) -> AuthCredentials | None:
        """Get current credentials."""
        return self._credentials

    def get_session_dict(self) -> dict[str, str]:
        """Get credentials as cookie dict for Instaloader."""
        if not self._credentials:
            return {}
        return {
            "sessionid": self._credentials.sessionid,
            "csrftoken": self._credentials.csrftoken,
            "ds_user_id": self._credentials.user_id,
        }

    def get_current_user(self) -> dict[str, Any]:
        """Get current user info (requires valid auth)."""
        if not self._credentials:
            raise ValueError("Not authenticated")

        loader = instaloader.Instaloader()
        loader.context._session.cookies.update(self.get_session_dict())

        username = loader.test_login()
        if not username:
            raise ValueError("Invalid or expired Instagram credentials")

        try:
            profile = instaloader.Profile.from_username(loader.context, username)
            return {
                "user_id": str(profile.userid),
                "username": profile.username,
                "full_name": profile.full_name,
                "followers": profile.followers,
                "following": profile.followees,
                "media_count": profile.mediacount,
                "is_private": profile.is_private,
                "authenticated": True,
            }
        except instaloader.exceptions.InstaloaderException:
            return {
                "user_id": self._credentials.user_id,
                "username": username,
                "authenticated": True,
            }

    @classmethod
    def extract_from_chrome(
        cls,
        profile: str = "Default",
        ignore_lock: bool = False,
    ) -> AuthCredentials:
        """Extract Instagram cookies from Chrome."""
        if browser_cookie3 is None:
            raise RuntimeError(
                "browser-cookie3 is required. Install with: pip install browser-cookie3"
            )

        cookie_file = cls._resolve_chrome_cookie_file(profile)
        prepared_cookie_file, temp_dir = cls._prepare_cookie_file(cookie_file, ignore_lock)

        try:
            cookie_jar = browser_cookie3.chrome(
                domain_name=COOKIE_DOMAIN,
                cookie_file=prepared_cookie_file,
            )
            return cls._extract_required_cookies(cookie_jar)
        except Exception as err:
            raise RuntimeError(f"Failed to extract Chrome cookies: {err}") from err
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()

    @classmethod
    def extract_from_firefox(
        cls,
        profile: str = "default-release",
        ignore_lock: bool = False,
    ) -> AuthCredentials:
        """Extract Instagram cookies from Firefox."""
        if browser_cookie3 is None:
            raise RuntimeError(
                "browser-cookie3 is required. Install with: pip install browser-cookie3"
            )

        cookie_file = cls._resolve_firefox_cookie_file(profile)
        prepared_cookie_file, temp_dir = cls._prepare_cookie_file(cookie_file, ignore_lock)

        try:
            cookie_jar = browser_cookie3.firefox(
                domain_name=COOKIE_DOMAIN,
                cookie_file=prepared_cookie_file,
            )
            return cls._extract_required_cookies(cookie_jar)
        except Exception as err:
            raise RuntimeError(f"Failed to extract Firefox cookies: {err}") from err
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()

    @staticmethod
    def _extract_required_cookies(cookie_jar: Any) -> AuthCredentials:
        cookies = {cookie.name: cookie.value for cookie in cookie_jar}

        sessionid = _coerce_string(cookies.get("sessionid"))
        csrftoken = _coerce_string(cookies.get("csrftoken"))
        user_id = _coerce_string(cookies.get("ds_user_id"))

        if not (sessionid and csrftoken and user_id):
            raise ValueError(
                "Could not find all required cookies. Make sure you're logged into "
                "instagram.com in the selected browser profile."
            )

        return AuthCredentials(
            sessionid=sessionid,
            csrftoken=csrftoken,
            user_id=user_id,
        )

    @staticmethod
    def _resolve_chrome_cookie_file(profile: str) -> Path | None:
        profile_name = profile or "Default"
        home = Path.home()

        candidates = [
            home / "Library/Application Support/Google/Chrome" / profile_name / "Cookies",
            home / ".config/google-chrome" / profile_name / "Cookies",
            home / ".config/chromium" / profile_name / "Cookies",
        ]
        return _first_existing(candidates)

    @staticmethod
    def _resolve_firefox_cookie_file(profile: str) -> Path | None:
        profile_name = profile or "default-release"
        profile_path = Path(profile_name).expanduser()
        if profile_path.suffix == ".sqlite" and profile_path.exists():
            return profile_path

        home = Path.home()
        direct_candidates = [
            home
            / "Library/Application Support/Firefox/Profiles"
            / profile_name
            / "cookies.sqlite",
            home / ".mozilla/firefox" / profile_name / "cookies.sqlite",
        ]

        found = _first_existing(direct_candidates)
        if found:
            return found

        glob_candidates = [
            home / "Library/Application Support/Firefox/Profiles",
            home / ".mozilla/firefox",
        ]

        for base in glob_candidates:
            if not base.exists():
                continue
            pattern = f"*{profile_name}*/cookies.sqlite"
            matches = sorted(base.glob(pattern))
            if matches:
                return matches[0]

        return None

    @staticmethod
    def _prepare_cookie_file(
        cookie_file: Path | None,
        ignore_lock: bool,
    ) -> tuple[str | None, tempfile.TemporaryDirectory[str] | None]:
        if cookie_file is None:
            return None, None

        if not ignore_lock:
            return str(cookie_file), None

        temp_dir = tempfile.TemporaryDirectory(prefix="glam-cookies-")
        temp_path = Path(temp_dir.name) / cookie_file.name
        shutil.copy2(cookie_file, temp_path)
        return str(temp_path), temp_dir


def _coerce_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None
