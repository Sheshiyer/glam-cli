from pathlib import Path

from gram.downloader import InstagramDownloader


class _Auth:
    def is_authenticated(self) -> bool:
        return True

    def get_session_dict(self) -> dict[str, str]:
        return {}


class _Highlight:
    title = "Road/Trip:2026?"

    def get_items(self):
        return [object()]


def test_highlights_titles_are_sanitized(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(InstagramDownloader, "_login", lambda self: None)

    downloader = InstagramDownloader(auth=_Auth(), output_dir=str(tmp_path))

    monkeypatch.setattr(
        "gram.downloader.instaloader.Profile.from_username",
        lambda _context, _username: object(),
    )
    monkeypatch.setattr(downloader.loader, "get_highlights", lambda _profile: [_Highlight()])

    targets: list[str] = []
    monkeypatch.setattr(
        downloader.loader,
        "download_storyitem",
        lambda _item, target: targets.append(target),
    )

    downloader.download_highlights("alice")

    assert targets == ["alice/highlights/Road_Trip_2026_"]
