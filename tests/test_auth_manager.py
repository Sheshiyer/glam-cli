from pathlib import Path

from gram.auth import AuthManager
from gram.config import ConfigManager


def test_auth_manager_loads_default_config_when_no_explicit_path(
    monkeypatch, tmp_path: Path
) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text(
        '{"sessionid":"session","csrftoken":"csrf","userId":"1234"}', encoding="utf-8"
    )

    monkeypatch.delenv("INSTAGRAM_SESSIONID", raising=False)
    monkeypatch.delenv("INSTAGRAM_CSRFTOKEN", raising=False)
    monkeypatch.delenv("INSTAGRAM_USER_ID", raising=False)
    monkeypatch.setattr(ConfigManager, "DEFAULT_CONFIG_PATH", config_file)

    auth = AuthManager()

    assert auth.is_authenticated() is True
    creds = auth.get_credentials()
    assert creds is not None
    assert creds.user_id == "1234"
