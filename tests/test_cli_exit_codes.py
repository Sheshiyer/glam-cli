from click.testing import CliRunner

from gram.cli import cli


def test_check_without_credentials_exits_nonzero(monkeypatch) -> None:
    monkeypatch.delenv("INSTAGRAM_SESSIONID", raising=False)
    monkeypatch.delenv("INSTAGRAM_CSRFTOKEN", raising=False)
    monkeypatch.delenv("INSTAGRAM_USER_ID", raising=False)
    monkeypatch.delenv("INSTAGRAM_DS_USER_ID", raising=False)
    monkeypatch.setattr("gram.config.ConfigManager.load_auth", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["check"])

    assert result.exit_code == 1
    assert "No credentials found" in result.output


def test_post_with_invalid_url_exits_nonzero() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["post", "not-a-url"])

    assert result.exit_code == 1
    assert "Invalid Instagram URL" in result.output


def test_login_without_browser_selection_exits_nonzero() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["login"])

    assert result.exit_code == 1
    assert "Specify --browser/--profile or one legacy profile flag" in result.output


def test_login_rejects_mixing_generic_and_legacy_browser_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["login", "--browser", "brave", "--profile", "Default", "--chrome-profile", "Default"],
    )

    assert result.exit_code == 1
    assert "Do not mix --browser/--profile with legacy browser flags" in result.output


def test_saved_without_credentials_exits_nonzero(monkeypatch) -> None:
    monkeypatch.delenv("INSTAGRAM_SESSIONID", raising=False)
    monkeypatch.delenv("INSTAGRAM_CSRFTOKEN", raising=False)
    monkeypatch.delenv("INSTAGRAM_USER_ID", raising=False)
    monkeypatch.delenv("INSTAGRAM_DS_USER_ID", raising=False)
    monkeypatch.setattr("gram.config.ConfigManager.load_auth", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["saved"])

    assert result.exit_code == 1
    assert "Authentication required" in result.output
