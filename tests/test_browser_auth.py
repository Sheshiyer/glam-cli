import types
from pathlib import Path

import pytest


def _fake_cookie(name: str, value: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(name=name, value=value)


def _disable_persistent_keychain_cache(monkeypatch, browser_auth_module) -> None:
    monkeypatch.setattr(
        browser_auth_module,
        "_read_persistent_osx_keychain_password",
        lambda cache_key: None,
        raising=False,
    )
    monkeypatch.setattr(
        browser_auth_module,
        "_write_persistent_osx_keychain_password",
        lambda cache_key, password: None,
        raising=False,
    )
    monkeypatch.setattr(
        browser_auth_module,
        "_clear_persistent_osx_keychain_password",
        lambda cache_key: None,
        raising=False,
    )


def test_diagnose_chrome_reports_missing_cookie_db(monkeypatch) -> None:
    from gram import browser_auth

    monkeypatch.setattr(browser_auth, "browser_cookie3", types.SimpleNamespace())
    monkeypatch.setattr(browser_auth, "_resolve_chrome_cookie_file", lambda profile: None)

    diagnosis = browser_auth.diagnose_chrome(profile="Default", ignore_lock=False)

    assert diagnosis.ok is False
    assert diagnosis.code == "cookie-file-missing"
    assert diagnosis.debug.browser == "chrome"
    assert diagnosis.debug.profile == "Default"
    assert diagnosis.debug.cookie_db_path is None


def test_extract_chrome_tracks_key_source_across_repeated_calls(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from gram import browser_auth

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

    monkeypatch.setattr(browser_auth, "browser_cookie3", fake_browser_cookie3)
    monkeypatch.setattr(browser_auth.sys, "platform", "darwin")
    monkeypatch.setattr(
        browser_auth,
        "_resolve_chrome_cookie_file",
        lambda profile: source_cookie_db,
    )
    _disable_persistent_keychain_cache(monkeypatch, browser_auth)

    first = browser_auth.extract_chrome(profile="Default", ignore_lock=False)
    second = browser_auth.extract_chrome(profile="Default", ignore_lock=False)

    assert first.credentials.user_id == "42"
    assert first.debug.key_source == "keychain"
    assert second.credentials.user_id == "42"
    assert second.debug.key_source == "cache-hit"
    assert key_calls == [("Chrome Safe Storage", "Chrome")]


def test_extract_chrome_uses_persistent_keychain_cache_across_processes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from gram import browser_auth

    source_cookie_db = tmp_path / "Cookies"
    source_cookie_db.write_text("sqlite", encoding="utf-8")

    browser_auth._OSX_KEYCHAIN_PASSWORD_CACHE.clear()

    def fake_get_osx_key(service: str, user: str) -> bytes:
        raise AssertionError(f"unexpected browser keychain lookup for {(service, user)}")

    def fake_chrome(*, domain_name: str, cookie_file: str | None = None, key_file=None):
        del key_file
        assert domain_name == "instagram.com"
        assert cookie_file == str(source_cookie_db)
        getter = browser_auth.browser_cookie3._get_osx_keychain_password
        assert getter("Chrome Safe Storage", "Chrome") == b"persisted-secret"
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

    monkeypatch.setattr(browser_auth, "browser_cookie3", fake_browser_cookie3)
    monkeypatch.setattr(browser_auth.sys, "platform", "darwin")
    monkeypatch.setattr(
        browser_auth,
        "_resolve_chrome_cookie_file",
        lambda profile: source_cookie_db,
    )
    monkeypatch.setattr(
        browser_auth,
        "_read_persistent_osx_keychain_password",
        lambda cache_key: b"persisted-secret",
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

    result = browser_auth.extract_chrome(profile="Default", ignore_lock=False)

    assert result.credentials.user_id == "42"
    assert result.debug.key_source == "persistent-cache-hit"


def test_extract_chrome_clears_stale_persistent_cache_and_retries_once(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from gram import browser_auth

    source_cookie_db = tmp_path / "Cookies"
    source_cookie_db.write_text("sqlite", encoding="utf-8")

    browser_auth._OSX_KEYCHAIN_PASSWORD_CACHE.clear()
    cache_key = ("Chrome Safe Storage", "Chrome")
    state = {"persistent_present": True, "attempts": 0}
    cleared: list[tuple[str, str]] = []
    written: list[tuple[tuple[str, str], bytes]] = []

    def fake_read_persistent(seen_cache_key: tuple[str, str]) -> bytes | None:
        assert seen_cache_key == cache_key
        if state["persistent_present"]:
            return b"stale-secret"
        return None

    def fake_write_persistent(seen_cache_key: tuple[str, str], password: bytes) -> None:
        assert seen_cache_key == cache_key
        written.append((seen_cache_key, password))

    def fake_clear_persistent(seen_cache_key: tuple[str, str]) -> None:
        assert seen_cache_key == cache_key
        cleared.append(seen_cache_key)
        state["persistent_present"] = False

    def fake_get_osx_key(service: str, user: str) -> bytes:
        assert (service, user) == cache_key
        if state["persistent_present"]:
            raise AssertionError("browser keychain lookup should wait until stale cache is cleared")
        return b"fresh-secret"

    def fake_chrome(*, domain_name: str, cookie_file: str | None = None, key_file=None):
        del key_file
        assert domain_name == "instagram.com"
        assert cookie_file == str(source_cookie_db)
        state["attempts"] += 1
        getter = browser_auth.browser_cookie3._get_osx_keychain_password
        secret = getter("Chrome Safe Storage", "Chrome")
        if state["attempts"] == 1:
            assert secret == b"stale-secret"
            raise RuntimeError("safe storage secret could not decrypt cookies")
        assert state["attempts"] == 2
        assert secret == b"fresh-secret"
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

    monkeypatch.setattr(browser_auth, "browser_cookie3", fake_browser_cookie3)
    monkeypatch.setattr(browser_auth.sys, "platform", "darwin")
    monkeypatch.setattr(
        browser_auth,
        "_resolve_chrome_cookie_file",
        lambda profile: source_cookie_db,
    )
    monkeypatch.setattr(
        browser_auth,
        "_read_persistent_osx_keychain_password",
        fake_read_persistent,
        raising=False,
    )
    monkeypatch.setattr(
        browser_auth,
        "_write_persistent_osx_keychain_password",
        fake_write_persistent,
        raising=False,
    )
    monkeypatch.setattr(
        browser_auth,
        "_clear_persistent_osx_keychain_password",
        fake_clear_persistent,
        raising=False,
    )

    result = browser_auth.extract_chrome(profile="Default", ignore_lock=False)

    assert result.credentials.user_id == "42"
    assert result.debug.key_source == "keychain"
    assert state["attempts"] == 2
    assert cleared == [cache_key]
    assert written == [(cache_key, b"fresh-secret")]


def test_extract_chrome_raises_typed_missing_cookie_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from gram import browser_auth

    source_cookie_db = tmp_path / "Cookies"
    source_cookie_db.write_text("sqlite", encoding="utf-8")

    def fake_chrome(*, domain_name: str, cookie_file: str | None = None, key_file=None):
        del domain_name, cookie_file, key_file
        return [_fake_cookie("csrftoken", "csrf")]

    monkeypatch.setattr(
        browser_auth,
        "browser_cookie3",
        types.SimpleNamespace(
            chrome=fake_chrome,
            _get_osx_keychain_password=lambda service, user: b"super-secret",
            CHROMIUM_DEFAULT_PASSWORD=b"peanuts",
        ),
    )
    monkeypatch.setattr(
        browser_auth,
        "_resolve_chrome_cookie_file",
        lambda profile: source_cookie_db,
    )

    with pytest.raises(browser_auth.BrowserInstagramCookiesMissingError) as exc_info:
        browser_auth.extract_chrome(profile="Default", ignore_lock=False)

    assert exc_info.value.code == "instagram-cookies-missing"
    assert exc_info.value.missing_cookie_names == ["sessionid", "ds_user_id"]


def test_extract_browser_supports_brave_dispatch(monkeypatch) -> None:
    from gram import browser_auth

    captured: dict[str, object] = {}

    def fake_extract_chromium(
        spec,
        profile: str,
        ignore_lock: bool,
    ):
        captured["browser"] = spec.slug
        captured["profile"] = profile
        captured["ignore_lock"] = ignore_lock
        return browser_auth.BrowserAuthResult(
            credentials=browser_auth.BrowserCookieCredentials(
                sessionid="sid",
                csrftoken="csrf",
                user_id="42",
            ),
            debug=browser_auth.BrowserAuthDebugInfo(
                browser=spec.slug,
                profile=profile,
                key_source="not-applicable",
            ),
        )

    monkeypatch.setattr(browser_auth, "_extract_chromium_browser", fake_extract_chromium)

    result = browser_auth.extract_browser(browser="brave", profile="Default", ignore_lock=True)

    assert captured == {
        "browser": "brave",
        "profile": "Default",
        "ignore_lock": True,
    }
    assert result.debug.browser == "brave"
