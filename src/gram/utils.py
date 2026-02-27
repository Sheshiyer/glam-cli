"""Utility functions for glam CLI."""

from __future__ import annotations

import re
from typing import TypedDict
from urllib.parse import urlparse


class ParsedInstagramUrl(TypedDict):
    """Parsed components from an Instagram URL."""

    type: str | None
    shortcode: str | None
    username: str | None


def validate_url(url: str) -> bool:
    """Validate Instagram URL format for content URLs."""
    if not url:
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain not in ("instagram.com", "www.instagram.com"):
        return False

    path = parsed.path.strip("/")
    if not path:
        return False

    parts = path.split("/")
    if len(parts) < 2:
        return False

    valid_types = ("p", "reel", "tv", "reels")
    if parts[0] not in valid_types:
        return False

    shortcode = parts[1]
    if not shortcode:
        return False

    return re.match(r"^[A-Za-z0-9_-]+$", shortcode) is not None


def format_username(username: str) -> str:
    """Clean and validate Instagram username."""
    if not username:
        raise ValueError("Username cannot be empty")

    cleaned = username.lstrip("@").lower()
    cleaned = re.sub(r"[^a-z0-9._]", "", cleaned)

    if len(cleaned) < 1:
        raise ValueError("Username cannot be empty")
    if len(cleaned) > 30:
        raise ValueError("Username too long (max 30 characters)")
    if cleaned.startswith(".") or cleaned.endswith("."):
        raise ValueError("Username cannot start or end with a period")
    if ".." in cleaned:
        raise ValueError("Username cannot contain consecutive periods")

    return cleaned


def humanize_number(num: int) -> str:
    """Convert large numbers to human-readable format."""
    if num < 1000:
        return str(num)

    for suffix, threshold in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if num >= threshold:
            value = num / threshold
            if value >= 100:
                return f"{int(value)}{suffix}"
            if value >= 10:
                return f"{value:.1f}{suffix}"
            return f"{value:.2f}{suffix}"

    return str(num)


def sanitize_filename(filename: str) -> str:
    """Sanitize a string for use as a filename."""
    invalid_chars = '<>:"/\\|?*'

    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, "_")

    sanitized = "".join(char for char in sanitized if ord(char) >= 32)
    sanitized = sanitized.strip(" .")

    if len(sanitized) > 200:
        sanitized = sanitized[:200]

    if not sanitized:
        return "unnamed"

    return sanitized


def parse_instagram_url(url: str) -> ParsedInstagramUrl:
    """Parse an Instagram URL and extract components."""
    result: ParsedInstagramUrl = {
        "type": None,
        "shortcode": None,
        "username": None,
    }

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain not in ("instagram.com", "www.instagram.com"):
        return result

    path = parsed.path.strip("/")
    if not path:
        return result

    parts = path.split("/")

    if parts[0] in ("p", "reel", "tv", "reels"):
        result["type"] = "post" if parts[0] == "p" else parts[0]
        if len(parts) > 1:
            result["shortcode"] = parts[1]
        return result

    if parts[0] == "stories" and len(parts) > 1:
        result["type"] = "story"
        result["username"] = parts[1]
        return result

    if parts[0] == "highlights" and len(parts) > 1:
        result["type"] = "highlight"
        result["username"] = parts[1]
        return result

    if len(parts) == 1 and parts[0]:
        try:
            result["username"] = format_username(parts[0])
            result["type"] = "profile"
        except ValueError:
            return result

    return result


def format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"

    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"

    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {secs}s"
