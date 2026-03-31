"""Authentication management for glam CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import instaloader

from gram.browser_auth import (
    BrowserAuthDiagnosis,
    BrowserAuthResult,
    diagnose_browser,
    extract_browser,
)


@dataclass
class AuthCredentials:
    """Instagram authentication credentials."""

    sessionid: str
    csrftoken: str
    user_id: str

    def is_valid(self) -> bool:
        """Check if the minimum fields for authenticated reads are present."""
        return bool(self.sessionid and self.user_id)

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


@dataclass
class AuthLoginResult:
    """Application-level login extraction result."""

    credentials: AuthCredentials
    debug: Any


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

        if sessionid and user_id:
            self._credentials = AuthCredentials(
                sessionid=sessionid,
                csrftoken=csrftoken or "",
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
        session = {
            "sessionid": self._credentials.sessionid,
            "ds_user_id": self._credentials.user_id,
        }
        if self._credentials.csrftoken:
            session["csrftoken"] = self._credentials.csrftoken
        return session

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
    def extract_browser_login(
        cls,
        browser: str,
        profile: str,
        ignore_lock: bool = False,
    ) -> AuthLoginResult:
        """Extract browser cookies plus debug information."""
        result = extract_browser(browser=browser, profile=profile, ignore_lock=ignore_lock)
        return cls._to_auth_login_result(result)

    @classmethod
    def diagnose_browser_login(
        cls,
        browser: str,
        profile: str,
        ignore_lock: bool = False,
    ) -> BrowserAuthDiagnosis:
        """Diagnose browser cookie extraction."""
        return diagnose_browser(browser=browser, profile=profile, ignore_lock=ignore_lock)

    @classmethod
    def extract_from_chrome(
        cls,
        profile: str = "Default",
        ignore_lock: bool = False,
    ) -> AuthCredentials:
        """Extract Instagram cookies from Chrome."""
        return cls.extract_browser_login(
            browser="chrome",
            profile=profile,
            ignore_lock=ignore_lock,
        ).credentials

    @classmethod
    def extract_from_firefox(
        cls,
        profile: str = "default-release",
        ignore_lock: bool = False,
    ) -> AuthCredentials:
        """Extract Instagram cookies from Firefox."""
        return cls.extract_browser_login(
            browser="firefox",
            profile=profile,
            ignore_lock=ignore_lock,
        ).credentials

    @staticmethod
    def _to_auth_login_result(result: BrowserAuthResult) -> AuthLoginResult:
        credentials = AuthCredentials(
            sessionid=result.credentials.sessionid,
            csrftoken=result.credentials.csrftoken,
            user_id=result.credentials.user_id,
        )
        return AuthLoginResult(credentials=credentials, debug=result.debug)


def _coerce_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""
