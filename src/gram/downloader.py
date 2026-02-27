"""Instagram content downloader using Instaloader."""

from __future__ import annotations

from itertools import islice
from pathlib import Path

import instaloader

from gram.auth import AuthManager
from gram.utils import sanitize_filename


class InstagramDownloader:
    """Downloads Instagram content using Instaloader."""

    def __init__(self, auth: AuthManager, output_dir: str | None = None) -> None:
        self.auth = auth
        self.output_dir = (
            Path(output_dir).expanduser()
            if output_dir
            else Path.home() / "Downloads" / "instagram"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.loader = instaloader.Instaloader(
            dirname_pattern=str(self.output_dir / "{target}"),
            filename_pattern="{date}_{shortcode}",
            download_pictures=True,
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=True,
            compress_json=False,
            post_metadata_txt_pattern="",
        )

        if auth.is_authenticated():
            self._login()

    def _login(self) -> None:
        """Login to Instagram using session cookies."""
        try:
            session_dict = self.auth.get_session_dict()
            self.loader.context._session.cookies.update(session_dict)

            username = self.loader.test_login()
            if not username:
                raise RuntimeError("Invalid or expired Instagram credentials")
        except Exception as err:
            raise RuntimeError(f"Login failed: {err}") from err

    def download_profile_posts(
        self,
        username: str,
        limit: int | None = None,
        resume: bool = False,
    ) -> None:
        """Download posts from a profile."""
        if limit is not None and limit < 0:
            raise ValueError("Limit must be non-negative")

        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            posts = profile.get_posts()

            if limit is not None:
                posts = islice(posts, limit)

            for post in posts:
                shortcode = getattr(post, "shortcode", None)
                if not isinstance(shortcode, str):
                    continue
                if resume and self._post_exists(username, shortcode):
                    continue
                self.loader.download_post(post, target=username)

        except instaloader.exceptions.ProfileNotExistsException as err:
            raise ValueError(f"Profile '{username}' does not exist") from err
        except instaloader.exceptions.PrivateProfileNotFollowedException as err:
            raise ValueError(
                f"Profile '{username}' is private. Authentication required."
            ) from err
        except instaloader.exceptions.InstaloaderException as err:
            raise RuntimeError(f"Failed to download profile: {err}") from err

    def download_post(self, url: str) -> None:
        """Download a single post by URL."""
        shortcode = self._extract_shortcode(url)

        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            self.loader.download_post(post, target=post.owner_username)
        except instaloader.exceptions.QueryReturnedNotFoundException as err:
            raise ValueError(f"Post not found: {url}") from err
        except instaloader.exceptions.InstaloaderException as err:
            raise RuntimeError(f"Failed to download post: {err}") from err

    def download_stories(self, username: str) -> None:
        """Download current stories (requires auth)."""
        if not self.auth.is_authenticated():
            raise ValueError("Authentication required to download stories")

        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            self.loader.download_stories(
                userids=[profile.userid],
                filename_target=str(self.output_dir / username / "stories"),
            )
        except instaloader.exceptions.InstaloaderException as err:
            raise RuntimeError(f"Failed to download stories: {err}") from err

    def download_highlights(self, username: str) -> None:
        """Download profile highlights (requires auth)."""
        if not self.auth.is_authenticated():
            raise ValueError("Authentication required to download highlights")

        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)

            for highlight in self.loader.get_highlights(profile):
                raw_title = getattr(highlight, "title", "")
                title = sanitize_filename(raw_title or "untitled")
                for item in highlight.get_items():
                    self.loader.download_storyitem(item, target=f"{username}/highlights/{title}")
        except instaloader.exceptions.InstaloaderException as err:
            raise RuntimeError(f"Failed to download highlights: {err}") from err

    @staticmethod
    def _extract_shortcode(url: str) -> str:
        """Extract shortcode from Instagram URL."""
        normalized_url = url.rstrip("/")
        parts = normalized_url.split("/")

        for index, part in enumerate(parts):
            if part in ("p", "reel", "reels", "tv") and index + 1 < len(parts):
                shortcode = parts[index + 1]
                if shortcode:
                    return shortcode

        raise ValueError(f"Could not extract shortcode from URL: {url}")

    def _post_exists(self, username: str, shortcode: str) -> bool:
        """Return True when a post artifact for shortcode already exists locally."""
        target_dir = self.output_dir / username
        if not target_dir.exists():
            return False
        return any(target_dir.glob(f"*_{shortcode}*"))
