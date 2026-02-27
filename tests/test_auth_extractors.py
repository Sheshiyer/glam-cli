import types
from pathlib import Path

from gram.auth import AuthManager


def _fake_cookie(name: str, value: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(name=name, value=value)


def test_extract_from_chrome_uses_copied_cookie_file_when_no_lock(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_cookie_db = tmp_path / "Cookies"
    source_cookie_db.write_text("sqlite", encoding="utf-8")

    captured: dict[str, str | None] = {"cookie_file": None}

    def fake_chrome(*, domain_name: str, cookie_file: str | None = None, key_file=None):
        del key_file
        assert domain_name == "instagram.com"
        captured["cookie_file"] = cookie_file
        return [
            _fake_cookie("sessionid", "sid"),
            _fake_cookie("csrftoken", "csrf"),
            _fake_cookie("ds_user_id", "42"),
        ]

    monkeypatch.setattr("gram.auth.browser_cookie3", types.SimpleNamespace(chrome=fake_chrome))
    monkeypatch.setattr(
        AuthManager,
        "_resolve_chrome_cookie_file",
        staticmethod(lambda profile: source_cookie_db),
    )

    creds = AuthManager.extract_from_chrome(profile="Profile 1", ignore_lock=True)

    assert creds.user_id == "42"
    assert captured["cookie_file"] is not None
    assert captured["cookie_file"] != str(source_cookie_db)


def test_extract_from_firefox_uses_requested_profile(monkeypatch, tmp_path: Path) -> None:
    cookie_db = tmp_path / "cookies.sqlite"
    cookie_db.write_text("sqlite", encoding="utf-8")

    seen: dict[str, str] = {}

    def fake_resolve(profile: str):
        seen["profile"] = profile
        return cookie_db

    def fake_firefox(*, domain_name: str, cookie_file: str | None = None, key_file=None):
        del key_file, domain_name, cookie_file
        return [
            _fake_cookie("sessionid", "sid"),
            _fake_cookie("csrftoken", "csrf"),
            _fake_cookie("ds_user_id", "999"),
        ]

    monkeypatch.setattr("gram.auth.browser_cookie3", types.SimpleNamespace(firefox=fake_firefox))
    monkeypatch.setattr(AuthManager, "_resolve_firefox_cookie_file", staticmethod(fake_resolve))

    creds = AuthManager.extract_from_firefox(profile="team-profile", ignore_lock=False)

    assert seen["profile"] == "team-profile"
    assert creds.user_id == "999"
