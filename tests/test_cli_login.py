import types

from click.testing import CliRunner

from gram.auth import AuthCredentials
from gram.cli import cli


def test_login_save_uses_extracted_credentials(monkeypatch) -> None:
    saved = {}
    creds = AuthCredentials(sessionid="sid", csrftoken="csrf", user_id="42")

    result_payload = types.SimpleNamespace(
        credentials=creds,
        debug=types.SimpleNamespace(to_dict=lambda: {"browser": "chrome"}),
    )

    def fake_extract(
        browser: str,
        profile: str,
        ignore_lock: bool = False,
    ) -> types.SimpleNamespace:
        assert browser == "chrome"
        assert profile == "Default"
        assert ignore_lock is False
        return result_payload

    def fake_save_auth(self, credentials: AuthCredentials) -> None:
        saved["credentials"] = credentials

    monkeypatch.setattr("gram.cli.AuthManager.extract_browser_login", fake_extract)
    monkeypatch.setattr("gram.cli.ConfigManager.save_auth", fake_save_auth)

    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--chrome-profile", "Default", "--save"])

    assert result.exit_code == 0
    assert saved["credentials"] == creds


def test_login_without_save_does_not_print_secrets(monkeypatch) -> None:
    creds = AuthCredentials(sessionid="sid", csrftoken="csrf", user_id="42")

    result_payload = types.SimpleNamespace(
        credentials=creds,
        debug=types.SimpleNamespace(to_dict=lambda: {"browser": "chrome"}),
    )

    def fake_extract(
        browser: str,
        profile: str,
        ignore_lock: bool = False,
    ) -> types.SimpleNamespace:
        del browser, profile, ignore_lock
        return result_payload

    monkeypatch.setattr("gram.cli.AuthManager.extract_browser_login", fake_extract)

    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--chrome-profile", "Default"])

    assert result.exit_code == 0
    assert "INSTAGRAM_SESSIONID=\"sid\"" not in result.output
    assert "Credentials were not printed for safety." in result.output


def test_login_print_env_outputs_values(monkeypatch) -> None:
    creds = AuthCredentials(sessionid="sid", csrftoken="csrf", user_id="42")

    result_payload = types.SimpleNamespace(
        credentials=creds,
        debug=types.SimpleNamespace(to_dict=lambda: {"browser": "chrome"}),
    )

    def fake_extract(
        browser: str,
        profile: str,
        ignore_lock: bool = False,
    ) -> types.SimpleNamespace:
        del browser, profile, ignore_lock
        return result_payload

    monkeypatch.setattr("gram.cli.AuthManager.extract_browser_login", fake_extract)

    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--chrome-profile", "Default", "--print-env"])

    assert result.exit_code == 0
    assert 'INSTAGRAM_SESSIONID="sid"' in result.output
    assert 'INSTAGRAM_CSRFTOKEN="csrf"' in result.output
    assert 'INSTAGRAM_USER_ID="42"' in result.output


def test_login_diagnose_outputs_browser_diagnosis(monkeypatch) -> None:
    diagnosis = types.SimpleNamespace(
        ok=False,
        code="cookie-file-missing",
        message="Could not find a Chrome cookie database for profile Default.",
        debug=types.SimpleNamespace(
            to_dict=lambda: {
                "browser": "chrome",
                "profile": "Default",
                "cookie_db_path": None,
                "key_source": "not-applicable",
            }
        ),
    )

    monkeypatch.setattr(
        "gram.cli.AuthManager.diagnose_browser_login",
        lambda browser, profile, ignore_lock=False: diagnosis,
        raising=False,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--chrome-profile", "Default", "--diagnose"])

    assert result.exit_code == 1
    assert "cookie-file-missing" in result.output
    assert "cookie_db_path" in result.output


def test_login_debug_auth_outputs_structured_debug_fields(monkeypatch) -> None:
    result_payload = types.SimpleNamespace(
        credentials=AuthCredentials(sessionid="sid", csrftoken="csrf", user_id="42"),
        debug=types.SimpleNamespace(
            to_dict=lambda: {
                "browser": "chrome",
                "profile": "Default",
                "cookie_db_path": "/tmp/Cookies",
                "key_source": "cache-hit",
            }
        ),
    )

    monkeypatch.setattr(
        "gram.cli.AuthManager.extract_browser_login",
        lambda browser, profile, ignore_lock=False: result_payload,
        raising=False,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--chrome-profile", "Default", "--debug-auth"])

    assert result.exit_code == 0
    assert "key_source" in result.output
    assert "cache-hit" in result.output


def test_login_generic_browser_profile_flow(monkeypatch) -> None:
    result_payload = types.SimpleNamespace(
        credentials=AuthCredentials(sessionid="sid", csrftoken="csrf", user_id="42"),
        debug=types.SimpleNamespace(
            to_dict=lambda: {
                "browser": "brave",
                "profile": "Default",
                "cookie_db_path": "/tmp/Cookies",
                "key_source": "not-applicable",
            }
        ),
    )
    captured: dict[str, object] = {}

    def fake_extract(
        browser: str,
        profile: str,
        ignore_lock: bool = False,
    ) -> types.SimpleNamespace:
        captured["browser"] = browser
        captured["profile"] = profile
        captured["ignore_lock"] = ignore_lock
        return result_payload

    monkeypatch.setattr("gram.cli.AuthManager.extract_browser_login", fake_extract)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["login", "--browser", "brave", "--profile", "Default", "--debug-auth"],
    )

    assert result.exit_code == 0
    assert captured == {"browser": "brave", "profile": "Default", "ignore_lock": False}
    assert "brave" in result.output
