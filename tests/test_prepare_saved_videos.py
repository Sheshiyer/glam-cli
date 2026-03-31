from __future__ import annotations

import json
from pathlib import Path

from scripts.prepare_saved_videos import collect_saved_videos, stage_saved_videos


def test_collect_saved_videos_orders_newest_first(tmp_path: Path) -> None:
    for name in [
        "2026-02-01_00-00-00_AAA111.mp4",
        "2026-03-02_00-00-00_BBB222.mp4",
        "2026-01-15_00-00-00_CCC333.mp4",
    ]:
        (tmp_path / name).write_text("video", encoding="utf-8")

    items = collect_saved_videos(tmp_path, limit=2)

    assert [item.video_path.name for item in items] == [
        "2026-03-02_00-00-00_BBB222.mp4",
        "2026-02-01_00-00-00_AAA111.mp4",
    ]
    assert [item.order for item in items] == [1, 2]


def test_stage_saved_videos_creates_ordered_links_and_manifest(tmp_path: Path) -> None:
    source_dir = tmp_path / "saved"
    output_dir = tmp_path / "staged"
    source_dir.mkdir()

    video = source_dir / "2026-03-02_00-00-00_BBB222.mp4"
    metadata = source_dir / "2026-03-02_00-00-00_BBB222.json"
    video.write_text("video", encoding="utf-8")
    metadata.write_text('{"node":{"shortcode":"BBB222"}}', encoding="utf-8")

    manifest_path = stage_saved_videos(source_dir, output_dir, limit=1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ordered_video = output_dir / "videos" / "01_2026-03-02_00-00-00_BBB222.mp4"
    ordered_json = output_dir / "videos" / "01_2026-03-02_00-00-00_BBB222.json"

    assert ordered_video.is_symlink()
    assert ordered_json.is_symlink()
    assert ordered_video.resolve() == video
    assert ordered_json.resolve() == metadata
    assert manifest["video_count"] == 1
    assert manifest["videos"][0]["video_source"] == str(video)
