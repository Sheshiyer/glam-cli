from pathlib import Path

from gram.downloader import InstagramDownloader


class _DummyAuth:
    def is_authenticated(self) -> bool:
        return False


class _FakePost:
    def __init__(self, shortcode: str) -> None:
        self.shortcode = shortcode


def _patch_profile_posts(monkeypatch, posts):
    class _FakeProfile:
        def get_posts(self):
            return posts

    def _fake_from_username(_context, _username):
        return _FakeProfile()

    monkeypatch.setattr(
        "gram.downloader.instaloader.Profile.from_username",
        _fake_from_username,
    )


def test_resume_skips_already_downloaded_posts(monkeypatch, tmp_path: Path) -> None:
    posts = [_FakePost("AAA111"), _FakePost("BBB222")]
    _patch_profile_posts(monkeypatch, posts)

    downloader = InstagramDownloader(auth=_DummyAuth(), output_dir=str(tmp_path))
    downloaded = []
    monkeypatch.setattr(
        downloader.loader,
        "download_post",
        lambda post, target: downloaded.append((post.shortcode, target)),
    )

    target_dir = tmp_path / "exampleuser"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "2024-01-01_00-00-00_UTC_AAA111.jpg").write_text("existing", encoding="utf-8")

    downloader.download_profile_posts("exampleuser", resume=True)

    assert downloaded == [("BBB222", "exampleuser")]


def test_without_resume_downloads_everything(monkeypatch, tmp_path: Path) -> None:
    posts = [_FakePost("AAA111"), _FakePost("BBB222")]
    _patch_profile_posts(monkeypatch, posts)

    downloader = InstagramDownloader(auth=_DummyAuth(), output_dir=str(tmp_path))
    downloaded = []
    monkeypatch.setattr(
        downloader.loader,
        "download_post",
        lambda post, target: downloaded.append((post.shortcode, target)),
    )

    target_dir = tmp_path / "exampleuser"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "2024-01-01_00-00-00_UTC_AAA111.jpg").write_text("existing", encoding="utf-8")

    downloader.download_profile_posts("exampleuser", resume=False)

    assert downloaded == [("AAA111", "exampleuser"), ("BBB222", "exampleuser")]
