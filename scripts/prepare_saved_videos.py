#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SavedVideo:
    order: int
    video_path: Path
    metadata_path: Path | None

    @property
    def basename(self) -> str:
        return self.video_path.stem


def collect_saved_videos(source_dir: Path, limit: int) -> list[SavedVideo]:
    videos = sorted(source_dir.glob("*.mp4"), reverse=True)
    selected = videos[:limit]
    result: list[SavedVideo] = []
    for order, video_path in enumerate(selected, start=1):
        metadata_path = video_path.with_suffix(".json")
        result.append(
            SavedVideo(
                order=order,
                video_path=video_path,
                metadata_path=metadata_path if metadata_path.exists() else None,
            )
        )
    return result


def reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def stage_saved_videos(source_dir: Path, output_dir: Path, limit: int) -> Path:
    videos = collect_saved_videos(source_dir, limit)
    if not videos:
        raise SystemExit(f"No .mp4 files found in {source_dir}")

    videos_dir = output_dir / "videos"
    reset_directory(videos_dir)

    manifest: dict[str, object] = {
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "sort_order": "filename_descending",
        "selection_rule": f"newest_{limit}_mp4_files",
        "video_count": len(videos),
        "videos": [],
    }

    for item in videos:
        ordered_name = f"{item.order:02d}_{item.video_path.name}"
        video_link = videos_dir / ordered_name
        video_link.symlink_to(item.video_path)

        metadata_link: Path | None = None
        if item.metadata_path is not None:
            metadata_link = videos_dir / f"{item.order:02d}_{item.metadata_path.name}"
            metadata_link.symlink_to(item.metadata_path)

        manifest["videos"].append(
            {
                "order": item.order,
                "basename": item.basename,
                "video_source": str(item.video_path),
                "video_link": str(video_link),
                "metadata_source": str(item.metadata_path) if item.metadata_path else None,
                "metadata_link": str(metadata_link) if metadata_link else None,
            }
        )

    manifest_path = output_dir / "manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    ordered_list_path = output_dir / "ordered_videos.txt"
    ordered_list_path.write_text(
        "\n".join(str((videos_dir / f"{item.order:02d}_{item.video_path.name}")) for item in videos)
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage the newest saved Instagram videos in deterministic newest-to-oldest order."
    )
    parser.add_argument("source_dir", type=Path, help="Directory containing downloaded saved media")
    parser.add_argument("output_dir", type=Path, help="Directory for ordered symlinks and manifest")
    parser.add_argument("--limit", type=int, default=20, help="Number of newest videos to stage")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = stage_saved_videos(args.source_dir.expanduser(), args.output_dir.expanduser(), args.limit)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
