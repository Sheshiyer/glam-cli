"""glam CLI - Main command definitions using Click."""

from __future__ import annotations

from typing import TypedDict, cast

import click

from gram import __version__
from gram.auth import AuthManager
from gram.browser_auth import (
    SUPPORTED_BROWSER_SLUGS,
    BrowserAuthError,
    resolve_browser_profile,
)
from gram.config import ConfigManager
from gram.downloader import InstagramDownloader
from gram.output import OutputFormatter
from gram.utils import format_username, validate_url


class CLIContext(TypedDict):
    """Typed structure for Click context storage."""

    config_path: str | None
    json: bool
    quiet: bool
    auth: AuthManager
    output: OutputFormatter


def _ctx_data(ctx: click.Context) -> CLIContext:
    return cast(CLIContext, ctx.obj)


def _fail(ctx: click.Context, message: str) -> None:
    """Print a user-facing error and terminate with non-zero status."""
    output = _ctx_data(ctx)["output"]
    output.error(message)
    ctx.exit(1)


def _emit_auth_debug(output: OutputFormatter, debug_payload: dict[str, object]) -> None:
    """Emit structured auth debug output."""
    output.data({"auth_debug": debug_payload})


def _serialize_payload(value: object) -> object:
    """Convert a structured object into a serializable payload."""
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()

    if isinstance(value, dict):
        return {key: _serialize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_payload(item) for item in value]

    value_dict = getattr(value, "__dict__", None)
    if isinstance(value_dict, dict):
        return {key: _serialize_payload(item) for key, item in value_dict.items()}

    return value


def _resolve_login_target(
    ctx: click.Context,
    browser: str | None,
    profile: str | None,
    chrome_profile: str | None,
    firefox_profile: str | None,
) -> tuple[str, str]:
    """Resolve the target browser/profile for login flows."""
    has_generic = browser is not None or profile is not None
    has_legacy = chrome_profile is not None or firefox_profile is not None

    if has_generic and has_legacy:
        _fail(ctx, "Do not mix --browser/--profile with legacy browser flags")

    if chrome_profile and firefox_profile:
        _fail(ctx, "Specify only one of --chrome-profile or --firefox-profile")

    if browser:
        return browser, resolve_browser_profile(browser, profile)

    if profile and not browser:
        _fail(ctx, "Use --profile only together with --browser")

    if chrome_profile:
        return "chrome", chrome_profile
    if firefox_profile:
        return "firefox", firefox_profile

    _fail(ctx, "Specify --browser/--profile or one legacy profile flag")
    raise AssertionError("unreachable")


@click.group()
@click.version_option(version=__version__, prog_name="glam")
@click.option("--config", "config", type=click.Path(), help="Path to config file")
@click.option("--json", "output_json", is_flag=True, help="JSON output")
@click.option("--quiet", "quiet", is_flag=True, help="Quiet mode")
@click.pass_context
def cli(ctx: click.Context, config: str | None, output_json: bool, quiet: bool) -> None:
    """Instagram CLI tool for downloading posts, stories, and profiles."""
    ctx.ensure_object(dict)
    ctx.obj = {
        "config_path": config,
        "json": output_json,
        "quiet": quiet,
        "auth": AuthManager(config),
        "output": OutputFormatter(json_output=output_json, quiet=quiet),
    }


@cli.command()
@click.pass_context
def whoami(ctx: click.Context) -> None:
    """Show logged-in account info."""
    data = _ctx_data(ctx)
    auth = data["auth"]
    output = data["output"]

    if not auth.is_authenticated():
        _fail(ctx, "Not authenticated. Run 'glam login' or set INSTAGRAM_SESSIONID.")

    try:
        user = auth.get_current_user()
        output.user_info(user)
    except Exception as err:
        _fail(ctx, f"Failed to get user info: {err}")


@cli.command()
@click.argument("username")
@click.option("--output", "output", type=click.Path(), help="Output directory")
@click.option("--posts", is_flag=True, help="Download posts")
@click.option("--stories", is_flag=True, help="Download stories")
@click.option("--highlights", is_flag=True, help="Download highlights")
@click.option("--limit", "limit", type=int, help="Limit number of posts")
@click.option("--resume", is_flag=True, help="Resume interrupted download")
@click.pass_context
def profile(
    ctx: click.Context,
    username: str,
    output: str | None,
    posts: bool,
    stories: bool,
    highlights: bool,
    limit: int | None,
    resume: bool,
) -> None:
    """Download profile posts and metadata."""
    data = _ctx_data(ctx)
    auth = data["auth"]
    output_fmt = data["output"]

    if not any([posts, stories, highlights]):
        posts = True

    try:
        downloader = InstagramDownloader(auth=auth, output_dir=output)

        if posts:
            output_fmt.info(f"Downloading posts from {username}...")
            downloader.download_profile_posts(
                username=format_username(username),
                limit=limit,
                resume=resume,
            )

        if stories:
            output_fmt.info(f"Downloading stories from {username}...")
            downloader.download_stories(username=format_username(username))

        if highlights:
            output_fmt.info(f"Downloading highlights from {username}...")
            downloader.download_highlights(username=format_username(username))

        output_fmt.success("Download complete")

    except Exception as err:
        _fail(ctx, f"Download failed: {err}")


@cli.command()
@click.argument("url")
@click.option("--output", "output", type=click.Path(), help="Output directory")
@click.pass_context
def post(ctx: click.Context, url: str, output: str | None) -> None:
    """Download a single post by URL."""
    data = _ctx_data(ctx)
    auth = data["auth"]
    output_fmt = data["output"]

    if not validate_url(url):
        _fail(ctx, "Invalid Instagram URL")

    try:
        downloader = InstagramDownloader(auth=auth, output_dir=output)
        output_fmt.info("Downloading post...")
        downloader.download_post(url)
        output_fmt.success("Download complete")
    except Exception as err:
        _fail(ctx, f"Download failed: {err}")


@cli.command()
@click.argument("username")
@click.option("--output", "output", type=click.Path(), help="Output directory")
@click.pass_context
def stories(ctx: click.Context, username: str, output: str | None) -> None:
    """Download current stories (requires authentication)."""
    data = _ctx_data(ctx)
    auth = data["auth"]
    output_fmt = data["output"]

    if not auth.is_authenticated():
        _fail(ctx, "Authentication required. Run 'glam login' first.")

    try:
        downloader = InstagramDownloader(auth=auth, output_dir=output)
        output_fmt.info(f"Downloading stories from {username}...")
        downloader.download_stories(username=format_username(username))
        output_fmt.success("Download complete")
    except Exception as err:
        _fail(ctx, f"Download failed: {err}")


@cli.command()
@click.argument("username")
@click.option("--output", "output", type=click.Path(), help="Output directory")
@click.pass_context
def highlights(ctx: click.Context, username: str, output: str | None) -> None:
    """Download profile highlights (requires authentication)."""
    data = _ctx_data(ctx)
    auth = data["auth"]
    output_fmt = data["output"]

    if not auth.is_authenticated():
        _fail(ctx, "Authentication required. Run 'glam login' first.")

    try:
        downloader = InstagramDownloader(auth=auth, output_dir=output)
        output_fmt.info(f"Downloading highlights from {username}...")
        downloader.download_highlights(username=format_username(username))
        output_fmt.success("Download complete")
    except Exception as err:
        _fail(ctx, f"Download failed: {err}")


@cli.command("saved")
@click.option("--output", "output", type=click.Path(), help="Output directory")
@click.option("--limit", "limit", type=int, help="Limit number of saved posts")
@click.option("--resume", is_flag=True, help="Resume interrupted download")
@click.pass_context
def saved_posts(
    ctx: click.Context,
    output: str | None,
    limit: int | None,
    resume: bool,
) -> None:
    """Download saved/bookmarked posts for the authenticated account."""
    data = _ctx_data(ctx)
    auth = data["auth"]
    output_fmt = data["output"]

    if not auth.is_authenticated():
        _fail(ctx, "Authentication required. Run 'glam login' first.")

    try:
        downloader = InstagramDownloader(auth=auth, output_dir=output)
        output_fmt.info("Downloading saved posts...")
        downloader.download_saved_posts(limit=limit, resume=resume)
        output_fmt.success("Download complete")
    except Exception as err:
        _fail(ctx, f"Download failed: {err}")


@cli.command()
@click.option("--browser", type=click.Choice(SUPPORTED_BROWSER_SLUGS), help="Browser name")
@click.option("--profile", help="Browser profile name")
@click.option("--chrome-profile", help="Chrome profile name")
@click.option("--firefox-profile", help="Firefox profile name")
@click.option("--save", is_flag=True, help="Save to config file")
@click.option(
    "--print-env",
    is_flag=True,
    help="Print export commands with raw credential values",
)
@click.option(
    "--no-lock",
    is_flag=True,
    help="Ignore browser lock by reading from a copied cookie DB",
)
@click.option(
    "--diagnose",
    is_flag=True,
    help="Diagnose browser cookie extraction without saving credentials",
)
@click.option(
    "--debug-auth",
    is_flag=True,
    help="Emit structured browser auth debug details",
)
@click.pass_context
def login(
    ctx: click.Context,
    browser: str | None,
    profile: str | None,
    chrome_profile: str | None,
    firefox_profile: str | None,
    save: bool,
    print_env: bool,
    no_lock: bool,
    diagnose: bool,
    debug_auth: bool,
) -> None:
    """Extract cookies from browser for authentication."""
    data = _ctx_data(ctx)
    output_fmt = data["output"]
    browser_name, profile_name = _resolve_login_target(
        ctx,
        browser,
        profile,
        chrome_profile,
        firefox_profile,
    )
    browser_label = browser_name.replace("-", " ").title()

    try:
        if diagnose:
            output_fmt.info(f"Diagnosing cookies from {browser_label} ({profile_name})...")
            diagnosis = AuthManager.diagnose_browser_login(
                browser=browser_name,
                profile=profile_name,
                ignore_lock=no_lock,
            )
            output_fmt.data(_serialize_payload(diagnosis))
            if not diagnosis.ok:
                ctx.exit(1)
            return

        output_fmt.info(f"Extracting cookies from {browser_label} ({profile_name})...")
        login_result = AuthManager.extract_browser_login(
            browser=browser_name,
            profile=profile_name,
            ignore_lock=no_lock,
        )
        credentials = login_result.credentials

        if debug_auth:
            _emit_auth_debug(output_fmt, _serialize_payload(login_result.debug))

        if save:
            config_manager = ConfigManager(data["config_path"])
            config_manager.save_auth(credentials)
            output_fmt.success(f"Cookies saved to {config_manager.config_path}")
            return

        output_fmt.success("Cookies extracted")
        if print_env:
            output_fmt.warning("Printing credentials to stdout. Treat this output as sensitive.")
            output_fmt.info(f'export INSTAGRAM_SESSIONID="{credentials.sessionid}"')
            output_fmt.info(f'export INSTAGRAM_CSRFTOKEN="{credentials.csrftoken}"')
            output_fmt.info(f'export INSTAGRAM_USER_ID="{credentials.user_id}"')
        else:
            output_fmt.info("Credentials were not printed for safety.")
            output_fmt.info("Use --save to persist in config or --print-env to emit shell exports.")

    except BrowserAuthError as err:
        if debug_auth:
            _emit_auth_debug(output_fmt, _serialize_payload(err.debug))
        _fail(ctx, f"Cookie extraction failed [{err.code}]: {err}")
    except Exception as err:
        _fail(ctx, f"Cookie extraction failed: {err}")


@cli.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Verify credentials are working."""
    data = _ctx_data(ctx)
    auth = data["auth"]
    output_fmt = data["output"]

    if auth.is_authenticated():
        try:
            user = auth.get_current_user()
            output_fmt.success("Credentials valid")
            output_fmt.user_info(user)
        except Exception as err:
            _fail(ctx, f"Credentials invalid: {err}")
        return

    output_fmt.error("No credentials found")
    output_fmt.info("Set INSTAGRAM_SESSIONID or run 'glam login'")
    ctx.exit(1)


def main() -> None:
    """CLI entry point for console scripts."""
    cli()
