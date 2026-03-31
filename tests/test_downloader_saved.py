from pathlib import Path

from gram.downloader import InstagramDownloader


class _Auth:
    def is_authenticated(self) -> bool:
        return True

    def get_session_dict(self) -> dict[str, str]:
        return {}


class _SavedPost:
    def __init__(self, shortcode: str) -> None:
        self.shortcode = shortcode


class _SavedProfile:
    def __init__(self, posts: list[_SavedPost]) -> None:
        self._posts = posts

    def get_saved_posts(self) -> list[_SavedPost]:
        return self._posts


def test_download_saved_posts_uses_saved_target(monkeypatch, tmp_path: Path) -> None:
    posts = [_SavedPost("AAA111"), _SavedPost("BBB222")]

    monkeypatch.setattr(InstagramDownloader, "_login", lambda self: None)

    downloader = InstagramDownloader(auth=_Auth(), output_dir=str(tmp_path))
    monkeypatch.setattr(downloader.loader, "test_login", lambda: "exampleuser")
    monkeypatch.setattr(
        "gram.downloader.instaloader.Profile.from_username",
        lambda _context, _username: _SavedProfile(posts),
    )

    downloaded: list[tuple[str, str]] = []
    monkeypatch.setattr(
        downloader.loader,
        "download_post",
        lambda post, target: downloaded.append((post.shortcode, target)),
    )

    downloader.download_saved_posts(limit=1)

    assert downloaded == [("AAA111", "saved")]


def test_saved_resume_skips_existing_posts(monkeypatch, tmp_path: Path) -> None:
    posts = [_SavedPost("AAA111"), _SavedPost("BBB222")]

    monkeypatch.setattr(InstagramDownloader, "_login", lambda self: None)

    downloader = InstagramDownloader(auth=_Auth(), output_dir=str(tmp_path))
    monkeypatch.setattr(downloader.loader, "test_login", lambda: "exampleuser")
    monkeypatch.setattr(
        "gram.downloader.instaloader.Profile.from_username",
        lambda _context, _username: _SavedProfile(posts),
    )

    saved_dir = tmp_path / "saved"
    saved_dir.mkdir(parents=True, exist_ok=True)
    (saved_dir / "2024-01-01_00-00-00_UTC_AAA111.jpg").write_text("existing", encoding="utf-8")

    downloaded: list[tuple[str, str]] = []
    monkeypatch.setattr(
        downloader.loader,
        "download_post",
        lambda post, target: downloaded.append((post.shortcode, target)),
    )

    downloader.download_saved_posts(resume=True)

    assert downloaded == [("BBB222", "saved")]
