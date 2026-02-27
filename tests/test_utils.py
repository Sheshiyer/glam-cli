import pytest

from gram.downloader import InstagramDownloader
from gram.utils import validate_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/p/ABC123/",
        "https://instagram.com/reel/ABC123",
        "https://www.instagram.com/tv/ABC123/",
        "https://www.instagram.com/reels/ABC123/",
    ],
)
def test_validate_url_accepts_supported_formats(url: str) -> None:
    assert validate_url(url) is True


def test_extract_shortcode_supports_tv_urls() -> None:
    shortcode = InstagramDownloader._extract_shortcode("https://www.instagram.com/tv/ABC123/")
    assert shortcode == "ABC123"
