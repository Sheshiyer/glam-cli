from click.testing import CliRunner

from gram.auth import AuthCredentials
from gram.cli import cli


def test_login_save_uses_extracted_credentials(monkeypatch) -> None:
    saved = {}
    creds = AuthCredentials(sessionid="sid", csrftoken="csrf", user_id="42")

    def fake_extract(profile: str = "Default", ignore_lock: bool = False) -> AuthCredentials:
        assert profile == "Default"
        assert ignore_lock is False
        return creds

    def fake_save_auth(self, credentials: AuthCredentials) -> None:
        saved["credentials"] = credentials

    monkeypatch.setattr("gram.cli.AuthManager.extract_from_chrome", fake_extract)
    monkeypatch.setattr("gram.cli.ConfigManager.save_auth", fake_save_auth)

    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--chrome-profile", "Default", "--save"])

    assert result.exit_code == 0
    assert saved["credentials"] == creds


def test_login_without_save_does_not_print_secrets(monkeypatch) -> None:
    creds = AuthCredentials(sessionid="sid", csrftoken="csrf", user_id="42")

    def fake_extract(profile: str = "Default", ignore_lock: bool = False) -> AuthCredentials:
        return creds

    monkeypatch.setattr("gram.cli.AuthManager.extract_from_chrome", fake_extract)

    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--chrome-profile", "Default"])

    assert result.exit_code == 0
    assert "INSTAGRAM_SESSIONID=\"sid\"" not in result.output
    assert "Credentials were not printed for safety." in result.output


def test_login_print_env_outputs_values(monkeypatch) -> None:
    creds = AuthCredentials(sessionid="sid", csrftoken="csrf", user_id="42")

    def fake_extract(profile: str = "Default", ignore_lock: bool = False) -> AuthCredentials:
        return creds

    monkeypatch.setattr("gram.cli.AuthManager.extract_from_chrome", fake_extract)

    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--chrome-profile", "Default", "--print-env"])

    assert result.exit_code == 0
    assert 'INSTAGRAM_SESSIONID="sid"' in result.output
    assert 'INSTAGRAM_CSRFTOKEN="csrf"' in result.output
    assert 'INSTAGRAM_USER_ID="42"' in result.output
