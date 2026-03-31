import types
from pathlib import Path

import gram.browser_auth as browser_auth
from gram.auth import AuthManager


def _fake_cookie(name: str, value: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(name=name, value=value)


def _disable_persistent_keychain_cache(monkeypatch) -> None:
    monkeypatch.setattr(
        browser_auth,
        "_read_persistent_osx_keychain_password",
        lambda cache_key: None,
        raising=False,
    )
    monkeypatch.setattr(
        browser_auth,
        "_write_persistent_osx_keychain_password",
        lambda cache_key, password: None,
        raising=False,
    )
    monkeypatch.setattr(
        browser_auth,
        "_clear_persistent_osx_keychain_password",
        lambda cache_key: None,
        raising=False,
    )


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

    monkeypatch.setattr(
        "gram.browser_auth.browser_cookie3",
        types.SimpleNamespace(chrome=fake_chrome),
    )
    monkeypatch.setattr(
        browser_auth,
        "_resolve_chrome_cookie_file",
        lambda profile: source_cookie_db,
    )

    creds = AuthManager.extract_from_chrome(profile="Profile 1", ignore_lock=True)

    assert creds.user_id == "42"
    assert captured["cookie_file"] is not None
    assert captured["cookie_file"] != str(source_cookie_db)


def test_extract_from_chrome_reuses_successful_osx_key_lookup(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_cookie_db = tmp_path / "Cookies"
    source_cookie_db.write_text("sqlite", encoding="utf-8")

    browser_auth._OSX_KEYCHAIN_PASSWORD_CACHE.clear()
    key_calls: list[tuple[str, str]] = []

    def fake_get_osx_key(service: str, user: str) -> bytes:
        key_calls.append((service, user))
        return b"super-secret"

    def fake_chrome(*, domain_name: str, cookie_file: str | None = None, key_file=None):
        del key_file
        assert domain_name == "instagram.com"
        assert cookie_file == str(source_cookie_db)
        getter = browser_auth.browser_cookie3._get_osx_keychain_password
        assert getter("Chrome Safe Storage", "Chrome") == b"super-secret"
        assert getter("Chrome Safe Storage", "Chrome") == b"super-secret"
        return [
            _fake_cookie("sessionid", "sid"),
            _fake_cookie("csrftoken", "csrf"),
            _fake_cookie("ds_user_id", "42"),
        ]

    fake_browser_cookie3 = types.SimpleNamespace(
        chrome=fake_chrome,
        _get_osx_keychain_password=fake_get_osx_key,
        CHROMIUM_DEFAULT_PASSWORD=b"peanuts",
    )
    monkeypatch.setattr("gram.browser_auth.browser_cookie3", fake_browser_cookie3)
    monkeypatch.setattr(browser_auth.sys, "platform", "darwin")
    monkeypatch.setattr(
        browser_auth,
        "_resolve_chrome_cookie_file",
        lambda profile: source_cookie_db,
    )
    _disable_persistent_keychain_cache(monkeypatch)

    first = AuthManager.extract_from_chrome(profile="Profile 1", ignore_lock=False)
    second = AuthManager.extract_from_chrome(profile="Profile 1", ignore_lock=False)

    assert first.user_id == "42"
    assert second.user_id == "42"
    assert key_calls == [("Chrome Safe Storage", "Chrome")]


def test_extract_from_chrome_does_not_cache_default_password_fallback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_cookie_db = tmp_path / "Cookies"
    source_cookie_db.write_text("sqlite", encoding="utf-8")

    browser_auth._OSX_KEYCHAIN_PASSWORD_CACHE.clear()
    key_calls: list[tuple[str, str]] = []

    def fake_get_osx_key(service: str, user: str) -> bytes:
        key_calls.append((service, user))
        return b"peanuts"

    def fake_chrome(*, domain_name: str, cookie_file: str | None = None, key_file=None):
        del key_file
        assert domain_name == "instagram.com"
        assert cookie_file == str(source_cookie_db)
        getter = browser_auth.browser_cookie3._get_osx_keychain_password
        assert getter("Chrome Safe Storage", "Chrome") == b"peanuts"
        assert getter("Chrome Safe Storage", "Chrome") == b"peanuts"
        return [
            _fake_cookie("sessionid", "sid"),
            _fake_cookie("csrftoken", "csrf"),
            _fake_cookie("ds_user_id", "42"),
        ]

    fake_browser_cookie3 = types.SimpleNamespace(
        chrome=fake_chrome,
        _get_osx_keychain_password=fake_get_osx_key,
        CHROMIUM_DEFAULT_PASSWORD=b"peanuts",
    )
    monkeypatch.setattr("gram.browser_auth.browser_cookie3", fake_browser_cookie3)
    monkeypatch.setattr(browser_auth.sys, "platform", "darwin")
    monkeypatch.setattr(
        browser_auth,
        "_resolve_chrome_cookie_file",
        lambda profile: source_cookie_db,
    )
    _disable_persistent_keychain_cache(monkeypatch)

    creds = AuthManager.extract_from_chrome(profile="Profile 1", ignore_lock=False)

    assert creds.user_id == "42"
    assert key_calls == [
        ("Chrome Safe Storage", "Chrome"),
        ("Chrome Safe Storage", "Chrome"),
    ]


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

    monkeypatch.setattr(
        "gram.browser_auth.browser_cookie3",
        types.SimpleNamespace(firefox=fake_firefox),
    )
    monkeypatch.setattr(browser_auth, "_resolve_firefox_cookie_file", fake_resolve)

    creds = AuthManager.extract_from_firefox(profile="team-profile", ignore_lock=False)

    assert seen["profile"] == "team-profile"
    assert creds.user_id == "999"


def test_extract_from_firefox_allows_missing_csrftoken(monkeypatch, tmp_path: Path) -> None:
    cookie_db = tmp_path / "cookies.sqlite"
    cookie_db.write_text("sqlite", encoding="utf-8")

    def fake_firefox(*, domain_name: str, cookie_file: str | None = None, key_file=None):
        del key_file, domain_name, cookie_file
        return [
            _fake_cookie("sessionid", "sid"),
            _fake_cookie("ds_user_id", "999"),
        ]

    monkeypatch.setattr(
        "gram.browser_auth.browser_cookie3",
        types.SimpleNamespace(firefox=fake_firefox),
    )
    monkeypatch.setattr(
        browser_auth,
        "_resolve_firefox_cookie_file",
        lambda profile: cookie_db,
    )

    creds = AuthManager.extract_from_firefox(profile="team-profile", ignore_lock=False)

    assert creds.sessionid == "sid"
    assert creds.csrftoken == ""
    assert creds.user_id == "999"
