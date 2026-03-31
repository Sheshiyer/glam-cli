#!/usr/bin/env python3
"""Prepare a deterministic newest-to-oldest video set from downloaded saved posts."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

FILENAME_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_(?P<shortcode>[^.]+)\.mp4$"
)


@dataclass(frozen=True)
class SavedVideo:
    """A local Instagram saved video paired with sortable filename metadata."""

    timestamp: str
    shortcode: str
    original_video_path: Path
    original_metadata_path: Path | None

    @property
    def sort_key(self) -> datetime:
        return datetime.strptime(self.timestamp, "%Y-%m-%d_%H-%M-%S")


def parse_saved_video(path: Path) -> SavedVideo | None:
    """Parse Instaloader's filename pattern and return structured video metadata."""
    match = FILENAME_RE.match(path.name)
    if match is None:
        return None

    metadata_path = path.with_suffix(".json")
    return SavedVideo(
        timestamp=match.group("timestamp"),
        shortcode=match.group("shortcode"),
        original_video_path=path.resolve(),
        original_metadata_path=metadata_path.resolve() if metadata_path.exists() else None,
    )


def collect_saved_videos(source_dir: Path) -> list[SavedVideo]:
    """Collect parseable MP4 files from the saved-media directory."""
    saved_videos: list[SavedVideo] = []

    for path in source_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".mp4":
            continue

        saved_video = parse_saved_video(path)
        if saved_video is not None:
            saved_videos.append(saved_video)

    return sorted(
        saved_videos,
        key=lambda video: (video.sort_key, video.shortcode),
        reverse=True,
    )


def reset_output_dir(output_dir: Path) -> None:
    """Clear and recreate the output directory."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def write_sorted_set(source_dir: Path, output_dir: Path, limit: int) -> Path:
    """Create a stable sorted output directory and a JSON manifest."""
    saved_videos = collect_saved_videos(source_dir)
    selected_videos = saved_videos[:limit]

    if not selected_videos:
        raise SystemExit(f"No parseable MP4 files found in {source_dir}")

    reset_output_dir(output_dir)

    manifest_path = output_dir / "sorted_videos.json"
    sorted_list_path = output_dir / "sorted_videos.txt"

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "limit": limit,
        "sort_basis": (
            "Descending by timestamp encoded in Instaloader filename pattern "
            "{date}_{shortcode}.mp4"
        ),
        "videos": [],
    }

    sorted_lines: list[str] = []

    for index, video in enumerate(selected_videos, start=1):
        rank_prefix = f"{index:02d}"
        sorted_video_path = output_dir / f"{rank_prefix}_{video.original_video_path.name}"
        sorted_video_path.symlink_to(video.original_video_path)

        sorted_metadata_path: Path | None = None
        if video.original_metadata_path is not None:
            sorted_metadata_path = output_dir / (
                f"{rank_prefix}_{video.original_metadata_path.name}"
            )
            sorted_metadata_path.symlink_to(video.original_metadata_path)

        entry = {
            "rank": index,
            **asdict(video),
            "original_video_path": str(video.original_video_path),
            "original_metadata_path": (
                str(video.original_metadata_path)
                if video.original_metadata_path is not None
                else None
            ),
            "sorted_video_path": str(sorted_video_path),
            "sorted_metadata_path": (
                str(sorted_metadata_path) if sorted_metadata_path is not None else None
            ),
        }
        manifest["videos"].append(entry)
        sorted_lines.append(f"{index:02d} {video.timestamp} {video.original_video_path.name}")

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sorted_list_path.write_text("\n".join(sorted_lines) + "\n", encoding="utf-8")

    return manifest_path


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Sort saved Instagram MP4s into a processing-ready newest-to-oldest set."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "Downloads" / "instagram" / "saved",
        help="Folder containing downloaded Instagram saved media.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / "Downloads" / "instagram" / "saved_processing" / "latest_20_videos",
        help="Output directory for the ordered processing set.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of newest videos to include.",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    source_dir = args.source.expanduser().resolve()
    output_dir = args.output.expanduser().resolve()

    if args.limit <= 0:
        raise SystemExit("--limit must be a positive integer")
    if not source_dir.exists():
        raise SystemExit(f"Source directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise SystemExit(f"Source path is not a directory: {source_dir}")

    manifest_path = write_sorted_set(source_dir, output_dir, args.limit)
    print(f"Sorted video manifest written to: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
