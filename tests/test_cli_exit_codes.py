from click.testing import CliRunner

from gram.cli import cli


def test_check_without_credentials_exits_nonzero(monkeypatch) -> None:
    monkeypatch.delenv("INSTAGRAM_SESSIONID", raising=False)
    monkeypatch.delenv("INSTAGRAM_CSRFTOKEN", raising=False)
    monkeypatch.delenv("INSTAGRAM_USER_ID", raising=False)
    monkeypatch.delenv("INSTAGRAM_DS_USER_ID", raising=False)

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
    assert "Specify --chrome-profile or --firefox-profile" in result.output
