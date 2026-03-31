"""Browser-specific cookie extraction and diagnostics."""

from __future__ import annotations

import base64
import binascii
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Any, Callable

browser_cookie3: Any
try:
    import browser_cookie3 as _browser_cookie3  # type: ignore[import-untyped]

    browser_cookie3 = _browser_cookie3
except ImportError:
    browser_cookie3 = None

COOKIE_DOMAIN = "instagram.com"
CHROME_OSX_KEYCHAIN_SERVICE = "Chrome Safe Storage"
CHROME_OSX_KEYCHAIN_ACCOUNT = "Chrome"
GLAM_OSX_KEYCHAIN_CACHE_SERVICE = "glam-cli Browser Auth Cache"
_OSX_KEYCHAIN_PASSWORD_CACHE: dict[tuple[str, str], bytes] = {}
_OSX_KEYCHAIN_SOURCE_BY_CACHE_KEY: dict[tuple[str, str], str] = {}
_OSX_KEYCHAIN_PASSWORD_CACHE_LOCK = Lock()
_OSX_KEYCHAIN_CACHE_MARKER = "__glam_cached_osx_keychain_password__"


@dataclass
class BrowserCookieCredentials:
    """Browser-derived credentials needed for Instagram auth."""

    sessionid: str
    csrftoken: str
    user_id: str


@dataclass(frozen=True)
class BrowserSpec:
    """Configuration for a supported browser extractor."""

    slug: str
    label: str
    family: str
    extractor_name: str
    default_profile: str
    osx_key_service: str | None = None
    osx_key_account: str | None = None
    cookie_file_resolver: Callable[[str], Path | None] | None = None
    allow_library_default: bool = False


@dataclass
class BrowserAuthDebugInfo:
    """Structured debug data for a browser auth attempt."""

    browser: str
    profile: str
    cookie_db_path: str | None = None
    prepared_cookie_db_path: str | None = None
    used_cookie_copy: bool = False
    keychain_service: str | None = None
    keychain_account: str | None = None
    key_source: str = "not-applicable"
    error_code: str | None = None
    missing_cookie_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "browser": self.browser,
            "profile": self.profile,
            "cookie_db_path": self.cookie_db_path,
            "prepared_cookie_db_path": self.prepared_cookie_db_path,
            "used_cookie_copy": self.used_cookie_copy,
            "keychain_service": self.keychain_service,
            "keychain_account": self.keychain_account,
            "key_source": self.key_source,
            "error_code": self.error_code,
            "missing_cookie_names": list(self.missing_cookie_names),
        }


@dataclass
class BrowserAuthResult:
    """Successful browser auth extraction result."""

    credentials: BrowserCookieCredentials
    debug: BrowserAuthDebugInfo


@dataclass
class BrowserAuthDiagnosis:
    """User-facing diagnosis of a browser auth attempt."""

    ok: bool
    code: str
    message: str
    debug: BrowserAuthDebugInfo

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "ok": self.ok,
            "code": self.code,
            "message": self.message,
            "debug": self.debug.to_dict(),
        }


class BrowserAuthError(RuntimeError):
    """Base class for browser auth failures."""

    code = "browser-auth-error"

    def __init__(
        self,
        message: str,
        debug: BrowserAuthDebugInfo,
        *,
        missing_cookie_names: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.debug = debug
        self.debug.error_code = self.code
        self.missing_cookie_names = missing_cookie_names or []
        if self.missing_cookie_names:
            self.debug.missing_cookie_names = list(self.missing_cookie_names)

    def to_diagnosis(self) -> BrowserAuthDiagnosis:
        """Convert the error into a diagnosis payload."""
        return BrowserAuthDiagnosis(
            ok=False,
            code=self.code,
            message=str(self),
            debug=self.debug,
        )


class BrowserCookieDependencyError(BrowserAuthError):
    code = "browser-cookie3-missing"


class BrowserCookieFileNotFoundError(BrowserAuthError):
    code = "cookie-file-missing"


class BrowserCookieExtractionError(BrowserAuthError):
    code = "cookie-extraction-failed"


class BrowserKeychainAccessError(BrowserAuthError):
    code = "keychain-access-failed"


class BrowserInstagramCookiesMissingError(BrowserAuthError):
    code = "instagram-cookies-missing"


def _resolve_chrome_cookie_file(profile: str) -> Path | None:
    profile_name = profile or "Default"
    home = Path.home()

    candidates = [
        home / "Library/Application Support/Google/Chrome" / profile_name / "Cookies",
        home / ".config/google-chrome" / profile_name / "Cookies",
        home / ".config/chromium" / profile_name / "Cookies",
    ]
    return _first_existing(candidates)


def _resolve_firefox_cookie_file(profile: str) -> Path | None:
    profile_name = profile or "default-release"
    profile_path = Path(profile_name).expanduser()
    if profile_path.suffix == ".sqlite" and profile_path.exists():
        return profile_path

    home = Path.home()
    direct_candidates = [
        home / "Library/Application Support/Firefox/Profiles" / profile_name / "cookies.sqlite",
        home / ".mozilla/firefox" / profile_name / "cookies.sqlite",
    ]

    found = _first_existing(direct_candidates)
    if found:
        return found

    glob_candidates = [
        home / "Library/Application Support/Firefox/Profiles",
        home / ".mozilla/firefox",
    ]

    for base in glob_candidates:
        if not base.exists():
            continue
        pattern = f"*{profile_name}*/cookies.sqlite"
        matches = sorted(base.glob(pattern))
        if matches:
            return matches[0]

    return None


SUPPORTED_BROWSERS: tuple[BrowserSpec, ...] = (
    BrowserSpec(
        slug="chrome",
        label="Chrome",
        family="chromium",
        extractor_name="chrome",
        default_profile="Default",
        osx_key_service="Chrome Safe Storage",
        osx_key_account="Chrome",
        cookie_file_resolver=lambda profile: _resolve_chrome_cookie_file(profile),
    ),
    BrowserSpec(
        slug="firefox",
        label="Firefox",
        family="firefox",
        extractor_name="firefox",
        default_profile="default-release",
        cookie_file_resolver=lambda profile: _resolve_firefox_cookie_file(profile),
    ),
    BrowserSpec(
        slug="brave",
        label="Brave",
        family="chromium",
        extractor_name="brave",
        default_profile="Default",
        osx_key_service="Brave Safe Storage",
        osx_key_account="Brave",
        allow_library_default=True,
    ),
    BrowserSpec(
        slug="arc",
        label="Arc",
        family="chromium",
        extractor_name="arc",
        default_profile="Default",
        osx_key_service="Arc Safe Storage",
        osx_key_account="Arc",
        allow_library_default=True,
    ),
    BrowserSpec(
        slug="chromium",
        label="Chromium",
        family="chromium",
        extractor_name="chromium",
        default_profile="Default",
        osx_key_service="Chromium Safe Storage",
        osx_key_account="Chromium",
        allow_library_default=True,
    ),
    BrowserSpec(
        slug="edge",
        label="Edge",
        family="chromium",
        extractor_name="edge",
        default_profile="Default",
        osx_key_service="Microsoft Edge Safe Storage",
        osx_key_account="Microsoft Edge",
        allow_library_default=True,
    ),
    BrowserSpec(
        slug="opera",
        label="Opera",
        family="chromium",
        extractor_name="opera",
        default_profile="Default",
        osx_key_service="Opera Safe Storage",
        osx_key_account="Opera",
        allow_library_default=True,
    ),
    BrowserSpec(
        slug="opera-gx",
        label="Opera GX",
        family="chromium",
        extractor_name="opera_gx",
        default_profile="Default",
        osx_key_service="Opera Safe Storage",
        osx_key_account="Opera",
        allow_library_default=True,
    ),
    BrowserSpec(
        slug="vivaldi",
        label="Vivaldi",
        family="chromium",
        extractor_name="vivaldi",
        default_profile="Default",
        osx_key_service="Vivaldi Safe Storage",
        osx_key_account="Vivaldi",
        allow_library_default=True,
    ),
)
SUPPORTED_BROWSER_SLUGS: tuple[str, ...] = tuple(spec.slug for spec in SUPPORTED_BROWSERS)
_BROWSER_SPECS_BY_SLUG = {spec.slug: spec for spec in SUPPORTED_BROWSERS}


def resolve_browser_profile(browser: str, profile: str | None) -> str:
    """Resolve a profile using the browser default when needed."""
    spec = _get_browser_spec(browser)
    return profile or spec.default_profile


def extract_browser(
    browser: str,
    profile: str,
    ignore_lock: bool = False,
) -> BrowserAuthResult:
    """Extract cookies for a supported browser."""
    spec = _get_browser_spec(browser)
    normalized_profile = profile or spec.default_profile
    if spec.family == "chromium":
        return _extract_chromium_browser(spec, normalized_profile, ignore_lock)
    if spec.family == "firefox":
        return _extract_firefox_browser(spec, normalized_profile, ignore_lock)
    raise ValueError(f"Unsupported browser family: {spec.family}")


def diagnose_browser(
    browser: str,
    profile: str,
    ignore_lock: bool = False,
) -> BrowserAuthDiagnosis:
    """Diagnose a browser auth attempt."""
    try:
        result = extract_browser(browser=browser, profile=profile, ignore_lock=ignore_lock)
    except BrowserAuthError as err:
        return err.to_diagnosis()

    return BrowserAuthDiagnosis(
        ok=True,
        code="ok",
        message="Browser authentication cookies extracted successfully.",
        debug=result.debug,
    )


def extract_chrome(profile: str = "Default", ignore_lock: bool = False) -> BrowserAuthResult:
    """Extract Instagram cookies from Chrome."""
    return extract_browser(browser="chrome", profile=profile, ignore_lock=ignore_lock)


def diagnose_chrome(
    profile: str = "Default",
    ignore_lock: bool = False,
) -> BrowserAuthDiagnosis:
    """Diagnose a Chrome auth attempt."""
    return diagnose_browser(browser="chrome", profile=profile, ignore_lock=ignore_lock)


def extract_firefox(
    profile: str = "default-release",
    ignore_lock: bool = False,
) -> BrowserAuthResult:
    """Extract Instagram cookies from Firefox."""
    return extract_browser(browser="firefox", profile=profile, ignore_lock=ignore_lock)


def _extract_chromium_browser(
    spec: BrowserSpec,
    profile: str,
    ignore_lock: bool,
) -> BrowserAuthResult:
    cache_key = _chromium_cache_key(spec)
    try:
        return _extract_chromium_browser_once(spec, profile, ignore_lock)
    except BrowserAuthError as err:
        if cache_key is not None and _should_retry_chromium_extraction(err):
            _clear_cached_osx_keychain_password(cache_key)
            _clear_persistent_osx_keychain_password(cache_key)
            return _extract_chromium_browser_once(spec, profile, ignore_lock)
        raise


def _extract_chromium_browser_once(
    spec: BrowserSpec,
    profile: str,
    ignore_lock: bool,
) -> BrowserAuthResult:
    debug = BrowserAuthDebugInfo(browser=spec.slug, profile=profile or spec.default_profile)
    _require_browser_cookie3(debug)

    cookie_file = spec.cookie_file_resolver(profile) if spec.cookie_file_resolver else None
    debug.cookie_db_path = _stringify_path(cookie_file)
    if cookie_file is None and not spec.allow_library_default:
        raise BrowserCookieFileNotFoundError(
            f"Could not find a {spec.label} cookie database for profile {debug.profile}.",
            debug,
        )

    prepared_cookie_file: str | None
    temp_dir: tempfile.TemporaryDirectory[str] | None
    if cookie_file is None:
        prepared_cookie_file, temp_dir = None, None
    else:
        prepared_cookie_file, temp_dir = _prepare_cookie_file(cookie_file, ignore_lock)
        debug.prepared_cookie_db_path = prepared_cookie_file
        debug.used_cookie_copy = prepared_cookie_file != str(cookie_file)

    cache_key = _chromium_cache_key(spec)
    if cache_key is not None:
        debug.keychain_service = spec.osx_key_service
        debug.keychain_account = spec.osx_key_account
        _clear_osx_keychain_source(cache_key)
        _install_browser_cookie3_osx_keychain_cache()

    extractor = getattr(browser_cookie3, spec.extractor_name, None)
    if extractor is None:
        raise BrowserCookieExtractionError(
            f"browser_cookie3 does not expose extractor '{spec.extractor_name}' for {spec.label}.",
            debug,
        )

    try:
        cookie_jar = extractor(domain_name=COOKIE_DOMAIN, cookie_file=prepared_cookie_file)
        debug.key_source = _resolve_key_source(cache_key)
        credentials = _extract_required_cookies(cookie_jar, debug)
        return BrowserAuthResult(credentials=credentials, debug=debug)
    except BrowserAuthError:
        raise
    except Exception as err:
        debug.key_source = _resolve_key_source(cache_key)
        raise _classify_chromium_extraction_error(spec, err, debug) from err
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def _extract_firefox_browser(
    spec: BrowserSpec,
    profile: str,
    ignore_lock: bool,
) -> BrowserAuthResult:
    debug = BrowserAuthDebugInfo(browser=spec.slug, profile=profile or spec.default_profile)
    _require_browser_cookie3(debug)

    cookie_file = spec.cookie_file_resolver(profile) if spec.cookie_file_resolver else None
    debug.cookie_db_path = _stringify_path(cookie_file)
    if cookie_file is None and not spec.allow_library_default:
        raise BrowserCookieFileNotFoundError(
            f"Could not find a {spec.label} cookie database for profile {debug.profile}.",
            debug,
        )

    prepared_cookie_file: str | None
    temp_dir: tempfile.TemporaryDirectory[str] | None
    if cookie_file is None:
        prepared_cookie_file, temp_dir = None, None
    else:
        prepared_cookie_file, temp_dir = _prepare_cookie_file(cookie_file, ignore_lock)
        debug.prepared_cookie_db_path = prepared_cookie_file
        debug.used_cookie_copy = prepared_cookie_file != str(cookie_file)

    extractor = getattr(browser_cookie3, spec.extractor_name, None)
    if extractor is None:
        raise BrowserCookieExtractionError(
            f"browser_cookie3 does not expose extractor '{spec.extractor_name}' for {spec.label}.",
            debug,
        )

    try:
        cookie_jar = extractor(domain_name=COOKIE_DOMAIN, cookie_file=prepared_cookie_file)
        credentials = _extract_required_cookies(cookie_jar, debug)
        return BrowserAuthResult(credentials=credentials, debug=debug)
    except BrowserAuthError:
        raise
    except Exception as err:
        raise BrowserCookieExtractionError(
            f"Failed to extract {spec.label} cookies: {err}",
            debug,
        ) from err
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def diagnose_firefox(
    profile: str = "default-release",
    ignore_lock: bool = False,
) -> BrowserAuthDiagnosis:
    """Diagnose a Firefox auth attempt."""
    return diagnose_browser(browser="firefox", profile=profile, ignore_lock=ignore_lock)


def _require_browser_cookie3(debug: BrowserAuthDebugInfo) -> None:
    if browser_cookie3 is None:
        raise BrowserCookieDependencyError(
            "browser-cookie3 is required. Install with: pip install browser-cookie3",
            debug,
        )


def _classify_chromium_extraction_error(
    spec: BrowserSpec,
    err: Exception,
    debug: BrowserAuthDebugInfo,
) -> BrowserAuthError:
    message = str(err)
    lowered = message.lower()
    if "safe storage" in lowered or "security" in lowered or "keychain" in lowered:
        return BrowserKeychainAccessError(
            f"Failed to access {spec.label} safe-storage credentials: {err}",
            debug,
        )
    return BrowserCookieExtractionError(f"Failed to extract {spec.label} cookies: {err}", debug)


def _extract_required_cookies(
    cookie_jar: Any,
    debug: BrowserAuthDebugInfo,
) -> BrowserCookieCredentials:
    cookies = {cookie.name: cookie.value for cookie in cookie_jar}

    sessionid = _coerce_string(cookies.get("sessionid"))
    csrftoken = _coerce_string(cookies.get("csrftoken"))
    user_id = _coerce_string(cookies.get("ds_user_id"))

    missing_cookie_names: list[str] = []
    if not sessionid:
        missing_cookie_names.append("sessionid")
    if not user_id:
        missing_cookie_names.append("ds_user_id")

    if missing_cookie_names:
        raise BrowserInstagramCookiesMissingError(
            (
                "Could not find the required Instagram session cookies. "
                "Make sure you're logged into instagram.com in the selected browser profile."
            ),
            debug,
            missing_cookie_names=missing_cookie_names,
        )

    return BrowserCookieCredentials(
        sessionid=sessionid,
        csrftoken=csrftoken,
        user_id=user_id,
    )


def _get_browser_spec(browser: str) -> BrowserSpec:
    normalized_browser = browser.strip().lower().replace("_", "-")
    spec = _BROWSER_SPECS_BY_SLUG.get(normalized_browser)
    if spec is None:
        raise ValueError(f"Unsupported browser: {browser}")
    return spec


def _prepare_cookie_file(
    cookie_file: Path,
    ignore_lock: bool,
) -> tuple[str, tempfile.TemporaryDirectory[str] | None]:
    if not ignore_lock:
        return str(cookie_file), None

    temp_dir = tempfile.TemporaryDirectory(prefix="glam-cookies-")
    temp_path = Path(temp_dir.name) / cookie_file.name
    shutil.copy2(cookie_file, temp_path)
    return str(temp_path), temp_dir


def _install_browser_cookie3_osx_keychain_cache() -> None:
    """Cache successful macOS Chromium key lookups for the current process."""
    if sys.platform != "darwin" or browser_cookie3 is None:
        return

    password_getter = getattr(browser_cookie3, "_get_osx_keychain_password", None)
    if password_getter is None or getattr(password_getter, _OSX_KEYCHAIN_CACHE_MARKER, False):
        return

    default_password = getattr(browser_cookie3, "CHROMIUM_DEFAULT_PASSWORD", b"peanuts")

    @wraps(password_getter)
    def cached_password_getter(osx_key_service: Any, osx_key_user: Any) -> bytes:
        cache_key = (_coerce_string(osx_key_service), _coerce_string(osx_key_user))
        cached_password = _get_cached_osx_keychain_password(cache_key)
        if cached_password is not None:
            _set_osx_keychain_source(cache_key, "cache-hit")
            return cached_password

        persistent_password = _read_persistent_osx_keychain_password(cache_key)
        if persistent_password is not None:
            _set_cached_osx_keychain_password(cache_key, persistent_password)
            _set_osx_keychain_source(cache_key, "persistent-cache-hit")
            return persistent_password

        try:
            password = password_getter(osx_key_service, osx_key_user)
        except Exception:
            _set_osx_keychain_source(cache_key, "keychain")
            raise

        if isinstance(password, bytes):
            if password == default_password:
                _set_osx_keychain_source(cache_key, "fallback")
                return password
            _set_cached_osx_keychain_password(cache_key, password)
            _write_persistent_osx_keychain_password(cache_key, password)
        _set_osx_keychain_source(cache_key, "keychain")
        return password

    setattr(cached_password_getter, _OSX_KEYCHAIN_CACHE_MARKER, True)
    browser_cookie3._get_osx_keychain_password = cached_password_getter


def _chromium_cache_key(spec: BrowserSpec) -> tuple[str, str] | None:
    if sys.platform != "darwin" or not spec.osx_key_service or not spec.osx_key_account:
        return None
    return (spec.osx_key_service, spec.osx_key_account)


def _get_cached_osx_keychain_password(cache_key: tuple[str, str]) -> bytes | None:
    with _OSX_KEYCHAIN_PASSWORD_CACHE_LOCK:
        return _OSX_KEYCHAIN_PASSWORD_CACHE.get(cache_key)


def _set_cached_osx_keychain_password(cache_key: tuple[str, str], password: bytes) -> None:
    with _OSX_KEYCHAIN_PASSWORD_CACHE_LOCK:
        _OSX_KEYCHAIN_PASSWORD_CACHE[cache_key] = password


def _has_cached_osx_keychain_password(cache_key: tuple[str, str]) -> bool:
    with _OSX_KEYCHAIN_PASSWORD_CACHE_LOCK:
        return cache_key in _OSX_KEYCHAIN_PASSWORD_CACHE


def _clear_cached_osx_keychain_password(cache_key: tuple[str, str]) -> None:
    with _OSX_KEYCHAIN_PASSWORD_CACHE_LOCK:
        _OSX_KEYCHAIN_PASSWORD_CACHE.pop(cache_key, None)
    _clear_osx_keychain_source(cache_key)


def _set_osx_keychain_source(cache_key: tuple[str, str], source: str) -> None:
    with _OSX_KEYCHAIN_PASSWORD_CACHE_LOCK:
        _OSX_KEYCHAIN_SOURCE_BY_CACHE_KEY.setdefault(cache_key, source)


def _clear_osx_keychain_source(cache_key: tuple[str, str]) -> None:
    with _OSX_KEYCHAIN_PASSWORD_CACHE_LOCK:
        _OSX_KEYCHAIN_SOURCE_BY_CACHE_KEY.pop(cache_key, None)


def _resolve_key_source(cache_key: tuple[str, str] | None) -> str:
    if cache_key is None:
        return "not-applicable"
    with _OSX_KEYCHAIN_PASSWORD_CACHE_LOCK:
        return _OSX_KEYCHAIN_SOURCE_BY_CACHE_KEY.get(cache_key, "fallback")


def _should_retry_chromium_extraction(err: BrowserAuthError) -> bool:
    if not isinstance(err, (BrowserCookieExtractionError, BrowserKeychainAccessError)):
        return False
    return err.debug.key_source in {"cache-hit", "persistent-cache-hit"}


def _persistent_osx_keychain_account(cache_key: tuple[str, str]) -> str:
    return f"{cache_key[0]}::{cache_key[1]}"


def _encode_persistent_osx_keychain_password(password: bytes) -> str:
    return base64.b64encode(password).decode("ascii")


def _decode_persistent_osx_keychain_password(encoded_password: str) -> bytes | None:
    normalized_password = encoded_password.strip()
    if not normalized_password:
        return None
    try:
        return base64.b64decode(normalized_password.encode("ascii"), validate=True)
    except (binascii.Error, ValueError):
        return None


def _read_persistent_osx_keychain_password(cache_key: tuple[str, str]) -> bytes | None:
    if sys.platform != "darwin":
        return None

    account = _persistent_osx_keychain_account(cache_key)
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-w",
                "-s",
                GLAM_OSX_KEYCHAIN_CACHE_SERVICE,
                "-a",
                account,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None

    password = _decode_persistent_osx_keychain_password(result.stdout)
    if password is None:
        _clear_persistent_osx_keychain_password(cache_key)
    return password


def _write_persistent_osx_keychain_password(
    cache_key: tuple[str, str],
    password: bytes,
) -> None:
    if sys.platform != "darwin":
        return

    account = _persistent_osx_keychain_account(cache_key)
    encoded_password = _encode_persistent_osx_keychain_password(password)
    try:
        subprocess.run(
            [
                "/usr/bin/security",
                "add-generic-password",
                "-U",
                "-s",
                GLAM_OSX_KEYCHAIN_CACHE_SERVICE,
                "-a",
                account,
                "-w",
                encoded_password,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return


def _clear_persistent_osx_keychain_password(cache_key: tuple[str, str]) -> None:
    if sys.platform != "darwin":
        return

    account = _persistent_osx_keychain_account(cache_key)
    try:
        subprocess.run(
            [
                "/usr/bin/security",
                "delete-generic-password",
                "-s",
                GLAM_OSX_KEYCHAIN_CACHE_SERVICE,
                "-a",
                account,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return


def _coerce_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _stringify_path(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path)
