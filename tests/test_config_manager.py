from pathlib import Path

from gram.config import ConfigManager


def test_load_supports_json5_comments_and_urls(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text(
        """
        {
          // comment line
          sessionid: "session",
          csrftoken: "csrf",
          userId: "123",
          endpoint: "https://www.instagram.com/p/ABC123/",
        }
        """,
        encoding="utf-8",
    )

    config = ConfigManager(str(config_file)).load()

    assert config["sessionid"] == "session"
    assert config["endpoint"] == "https://www.instagram.com/p/ABC123/"


def test_load_falls_back_to_legacy_path(monkeypatch, tmp_path: Path) -> None:
    default_path = tmp_path / "glam" / "config.json5"
    legacy_path = tmp_path / "gram" / "config.json5"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(
        '{"sessionid": "session", "csrftoken": "csrf", "userId": "777"}',
        encoding="utf-8",
    )

    monkeypatch.setattr(ConfigManager, "DEFAULT_CONFIG_PATH", default_path)
    monkeypatch.setattr(ConfigManager, "LEGACY_CONFIG_PATH", legacy_path)

    manager = ConfigManager()
    creds = manager.load_auth()

    assert creds is not None
    assert creds.user_id == "777"


def test_save_writes_new_default_even_when_legacy_exists(monkeypatch, tmp_path: Path) -> None:
    default_path = tmp_path / "glam" / "config.json5"
    legacy_path = tmp_path / "gram" / "config.json5"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text('{"sessionid": "old"}', encoding="utf-8")

    monkeypatch.setattr(ConfigManager, "DEFAULT_CONFIG_PATH", default_path)
    monkeypatch.setattr(ConfigManager, "LEGACY_CONFIG_PATH", legacy_path)

    manager = ConfigManager()
    manager.save({"sessionid": "new"})

    assert default_path.exists()
    assert "new" in default_path.read_text(encoding="utf-8")
