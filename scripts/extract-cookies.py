#!/usr/bin/env python3
"""Standalone cookie extraction utility for glam-cli."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def extract_chrome_cookies(
    profile: str = "Default",
    domain: str = "instagram.com",
) -> dict[str, str]:
    """Extract cookies from Chrome browser."""
    try:
        import browser_cookie3  # type: ignore[import-untyped]
    except ImportError:
        print("Error: browser_cookie3 not installed")
        print("Install with: pip install browser-cookie3")
        sys.exit(1)

    try:
        print(f"Extracting cookies from Chrome profile: {profile}")
        cookie_jar = browser_cookie3.chrome(domain_name=domain)
        cookies = {cookie.name: cookie.value for cookie in cookie_jar}
        return {
            "sessionid": str(cookies.get("sessionid", "")),
            "csrftoken": str(cookies.get("csrftoken", "")),
            "user_id": str(cookies.get("ds_user_id", "")),
        }
    except Exception as err:
        print(f"Error extracting Chrome cookies: {err}")
        sys.exit(1)


def extract_firefox_cookies(
    profile: str = "default-release", domain: str = "instagram.com"
) -> dict[str, str]:
    """Extract cookies from Firefox browser."""
    try:
        import browser_cookie3  # type: ignore[import-untyped]
    except ImportError:
        print("Error: browser_cookie3 not installed")
        print("Install with: pip install browser-cookie3")
        sys.exit(1)

    try:
        print(f"Extracting cookies from Firefox profile: {profile}")
        cookie_jar = browser_cookie3.firefox(domain_name=domain)
        cookies = {cookie.name: cookie.value for cookie in cookie_jar}
        return {
            "sessionid": str(cookies.get("sessionid", "")),
            "csrftoken": str(cookies.get("csrftoken", "")),
            "user_id": str(cookies.get("ds_user_id", "")),
        }
    except Exception as err:
        print(f"Error extracting Firefox cookies: {err}")
        sys.exit(1)


def print_shell_export(cookies: dict[str, str]) -> None:
    """Print cookies as shell export statements."""
    print("\n# Copy these to your ~/.zshrc or ~/.bashrc:\n")

    if cookies.get("sessionid"):
        print(f'export INSTAGRAM_SESSIONID="{cookies["sessionid"]}"')
    else:
        print("# Warning: sessionid not found")

    if cookies.get("csrftoken"):
        print(f'export INSTAGRAM_CSRFTOKEN="{cookies["csrftoken"]}"')
    else:
        print("# Warning: csrftoken not found")

    if cookies.get("user_id"):
        print(f'export INSTAGRAM_USER_ID="{cookies["user_id"]}"')
    else:
        print("# Warning: user_id not found")

    print()


def print_json_config(cookies: dict[str, str], output_path: str | Path | None = None) -> None:
    """Print cookies as JSON config."""
    config: dict[str, Any] = {
        "sessionid": cookies.get("sessionid", ""),
        "csrftoken": cookies.get("csrftoken", ""),
        "userId": cookies.get("user_id", ""),
    }

    json_output = json.dumps(config, indent=2)

    if output_path:
        path = Path(output_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json_output, encoding="utf-8")

        print(f"\nConfig saved to: {path}")
        os.chmod(path, 0o600)
        print("Permissions set to 600 (owner-only read)")
    else:
        print("\n# Add this to ~/.config/glam/config.json5:\n")
        print(json_output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Instagram cookies from browser for glam-cli"
    )
    parser.add_argument("--chrome", metavar="PROFILE", help="Extract from Chrome profile")
    parser.add_argument("--firefox", metavar="PROFILE", help="Extract from Firefox profile")
    parser.add_argument(
        "--save",
        metavar="PATH",
        help="Save to config file (default: ~/.config/glam/config.json5)",
    )
    parser.add_argument("--shell", action="store_true", help="Print shell export commands")

    args = parser.parse_args()

    if args.chrome is not None:
        profile = args.chrome if args.chrome else "Default"
        cookies = extract_chrome_cookies(profile)
    elif args.firefox is not None:
        profile = args.firefox if args.firefox else "default-release"
        cookies = extract_firefox_cookies(profile)
    else:
        print("No browser specified, trying Chrome Default...")
        cookies = extract_chrome_cookies("Default")

    missing = []
    for key in ("sessionid", "csrftoken", "user_id"):
        if not cookies.get(key):
            missing.append(key)

    if missing:
        print(f"\nWarning: Missing cookies: {', '.join(missing)}")
        print("Make sure you're logged into instagram.com in the browser.")
        sys.exit(1)

    print("\nAll cookies found")

    if args.shell:
        print_shell_export(cookies)
    elif args.save:
        print_json_config(cookies, args.save)
    else:
        print_shell_export(cookies)
        print("\nOr save to config:")
        default_path = Path.home() / ".config" / "glam" / "config.json5"
        print_json_config(cookies, default_path)


if __name__ == "__main__":
    main()
