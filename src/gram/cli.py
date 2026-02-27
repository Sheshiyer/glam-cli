"""glam CLI - Main command definitions using Click."""

from __future__ import annotations

from typing import TypedDict, cast

import click

from gram import __version__
from gram.auth import AuthManager
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


@cli.command()
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
@click.pass_context
def login(
    ctx: click.Context,
    chrome_profile: str | None,
    firefox_profile: str | None,
    save: bool,
    print_env: bool,
    no_lock: bool,
) -> None:
    """Extract cookies from browser for authentication."""
    data = _ctx_data(ctx)
    output_fmt = data["output"]

    try:
        if chrome_profile:
            output_fmt.info(f"Extracting cookies from Chrome ({chrome_profile})...")
            credentials = AuthManager.extract_from_chrome(
                profile=chrome_profile,
                ignore_lock=no_lock,
            )
        elif firefox_profile:
            output_fmt.info(f"Extracting cookies from Firefox ({firefox_profile})...")
            credentials = AuthManager.extract_from_firefox(
                profile=firefox_profile,
                ignore_lock=no_lock,
            )
        else:
            _fail(ctx, "Specify --chrome-profile or --firefox-profile")
            return

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
