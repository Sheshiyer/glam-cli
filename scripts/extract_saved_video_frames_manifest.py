#!/usr/bin/env python3
"""Extract frames from a staged Instagram video set and build merged metadata JSON."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HASHTAG_RE = re.compile(r"#(\w+)")


def run_json_command(command: list[str]) -> dict:
    """Run a command that returns JSON to stdout."""
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def load_staged_manifest(staged_dir: Path) -> list[dict]:
    """Load the sorted video manifest from the staging directory."""
    manifest_path = staged_dir / "sorted_videos.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing staged manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    videos = manifest.get("videos")
    if not isinstance(videos, list) or not videos:
        raise SystemExit(f"No videos found in staged manifest: {manifest_path}")
    return videos


def reset_output_dir(output_dir: Path) -> None:
    """Clear the output directory before regenerating results."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def rational_to_float(value: str | None) -> float | None:
    """Convert an ffprobe rational string like 30000/1001 to float."""
    if not value:
        return None
    if "/" not in value:
        try:
            return float(value)
        except ValueError:
            return None

    numerator, denominator = value.split("/", maxsplit=1)
    try:
        denominator_value = float(denominator)
        if denominator_value == 0:
            return None
        return float(numerator) / denominator_value
    except ValueError:
        return None


def extract_ffprobe_summary(ffprobe_data: dict) -> dict:
    """Extract the most useful ffprobe fields into a compact summary."""
    format_data = ffprobe_data.get("format", {})
    streams = ffprobe_data.get("streams", [])
    video_stream = next(
        (stream for stream in streams if stream.get("codec_type") == "video"),
        {},
    )
    audio_stream = next(
        (stream for stream in streams if stream.get("codec_type") == "audio"),
        {},
    )

    duration_seconds = float(format_data.get("duration", 0) or 0)
    fps = rational_to_float(video_stream.get("r_frame_rate"))
    nb_frames = video_stream.get("nb_frames")
    total_frames = int(nb_frames) if nb_frames is not None else None

    return {
        "format_name": format_data.get("format_name"),
        "duration_seconds": duration_seconds,
        "size_bytes": int(format_data.get("size", 0) or 0),
        "bit_rate": int(format_data.get("bit_rate", 0) or 0),
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "display_aspect_ratio": video_stream.get("display_aspect_ratio"),
        "fps": fps,
        "estimated_total_frames": total_frames,
        "has_audio": bool(audio_stream),
        "audio_channels": audio_stream.get("channels"),
        "audio_sample_rate": audio_stream.get("sample_rate"),
    }


def get_caption_text(sidecar_node: dict) -> str:
    """Return the primary caption text if available."""
    caption_edges = (
        sidecar_node.get("edge_media_to_caption", {})
        .get("edges", [])
    )
    if not caption_edges:
        return ""

    caption_node = caption_edges[0].get("node", {})
    caption_text = caption_node.get("text", "")
    return caption_text if isinstance(caption_text, str) else ""


def extract_instagram_summary(sidecar_data: dict, fallback_timestamp: str, shortcode: str) -> dict:
    """Extract a compact Instagram-side summary from the saved sidecar JSON."""
    node = sidecar_data.get("node", {})
    owner = node.get("owner", {}) if isinstance(node.get("owner"), dict) else {}
    music = (
        node.get("clips_music_attribution_info", {})
        if isinstance(node.get("clips_music_attribution_info"), dict)
        else {}
    )
    caption_text = get_caption_text(node)

    return {
        "shortcode": node.get("shortcode", shortcode),
        "typename": node.get("__typename"),
        "owner_username": owner.get("username"),
        "owner_id": owner.get("id"),
        "owner_is_verified": owner.get("is_verified"),
        "posted_at_timestamp": node.get("taken_at_timestamp", fallback_timestamp),
        "caption": caption_text,
        "hashtags": HASHTAG_RE.findall(caption_text),
        "like_count": (
            node.get("edge_media_preview_like", {})
            .get("count")
        ),
        "comment_count": (
            node.get("edge_media_to_comment", {})
            .get("count")
        ),
        "dimensions": node.get("dimensions"),
        "video_view_count": node.get("video_view_count"),
        "video_play_count": node.get("video_play_count"),
        "display_url": node.get("display_url"),
        "music": {
            "artist_name": music.get("artist_name"),
            "song_name": music.get("song_name"),
            "audio_id": music.get("audio_id"),
            "uses_original_audio": music.get("uses_original_audio"),
        },
    }


def run_ffprobe(video_path: Path) -> dict:
    """Return full ffprobe JSON for a video."""
    return run_json_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
    )


def extract_frames(video_path: Path, frame_dir: Path) -> int:
    """Extract every frame from the video into the target directory."""
    frame_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-map",
            "0:v:0",
            "-vsync",
            "0",
            "-qscale:v",
            "2",
            str(frame_dir / "frame_%06d.jpg"),
        ],
        check=True,
    )
    return len(list(frame_dir.glob("frame_*.jpg")))


def build_batch_summary(video_entries: list[dict]) -> dict:
    """Build a synthesis-friendly summary from the processed video entries."""
    total_duration_seconds = sum(
        entry["ffprobe_summary"]["duration_seconds"] for entry in video_entries
    )
    total_frames_extracted = sum(
        entry["frame_extraction"]["frame_count"] for entry in video_entries
    )
    total_size_bytes = sum(
        entry["ffprobe_summary"]["size_bytes"] for entry in video_entries
    )

    owner_counts = Counter(
        entry["instagram_summary"]["owner_username"]
        for entry in video_entries
        if entry["instagram_summary"]["owner_username"]
    )
    hashtag_counts = Counter(
        hashtag
        for entry in video_entries
        for hashtag in entry["instagram_summary"]["hashtags"]
    )
    music_counts = Counter(
        (
            entry["instagram_summary"]["music"].get("artist_name"),
            entry["instagram_summary"]["music"].get("song_name"),
        )
        for entry in video_entries
        if entry["instagram_summary"]["music"].get("artist_name")
        or entry["instagram_summary"]["music"].get("song_name")
    )

    longest_video = max(
        video_entries,
        key=lambda entry: entry["ffprobe_summary"]["duration_seconds"],
    )
    shortest_video = min(
        video_entries,
        key=lambda entry: entry["ffprobe_summary"]["duration_seconds"],
    )

    return {
        "video_count": len(video_entries),
        "total_duration_seconds": total_duration_seconds,
        "total_duration_minutes": total_duration_seconds / 60,
        "total_frames_extracted": total_frames_extracted,
        "total_size_bytes": total_size_bytes,
        "top_owners": [
            {"owner_username": owner, "count": count}
            for owner, count in owner_counts.most_common(10)
        ],
        "top_hashtags": [
            {"hashtag": hashtag, "count": count}
            for hashtag, count in hashtag_counts.most_common(15)
        ],
        "music_tracks": [
            {"artist_name": artist, "song_name": song, "count": count}
            for (artist, song), count in music_counts.most_common(15)
        ],
        "longest_video": {
            "rank": longest_video["rank"],
            "shortcode": longest_video["shortcode"],
            "staged_video_name": Path(longest_video["paths"]["staged_video_path"]).name,
            "duration_seconds": longest_video["ffprobe_summary"]["duration_seconds"],
        },
        "shortest_video": {
            "rank": shortest_video["rank"],
            "shortcode": shortest_video["shortcode"],
            "staged_video_name": Path(shortest_video["paths"]["staged_video_path"]).name,
            "duration_seconds": shortest_video["ffprobe_summary"]["duration_seconds"],
        },
    }


def process_videos(staged_dir: Path, output_dir: Path) -> Path:
    """Process every staged video and write the batch manifest."""
    staged_entries = load_staged_manifest(staged_dir)
    reset_output_dir(output_dir)

    frames_root = output_dir / "frames"
    ffprobe_root = output_dir / "ffprobe"
    merged_root = output_dir / "merged"
    frames_root.mkdir(parents=True, exist_ok=True)
    ffprobe_root.mkdir(parents=True, exist_ok=True)
    merged_root.mkdir(parents=True, exist_ok=True)

    batch_entries: list[dict] = []

    for staged_entry in staged_entries:
        rank = int(staged_entry["rank"])
        shortcode = staged_entry["shortcode"]
        staged_video_path = Path(staged_entry["sorted_video_path"])
        staged_metadata_path = (
            Path(staged_entry["sorted_metadata_path"])
            if staged_entry.get("sorted_metadata_path")
            else None
        )

        ffprobe_data = run_ffprobe(staged_video_path)
        ffprobe_summary = extract_ffprobe_summary(ffprobe_data)

        frame_dir = frames_root / f"{rank:02d}_{shortcode}"
        frame_count = extract_frames(staged_video_path, frame_dir)

        sidecar_data = {}
        instagram_summary = {
            "shortcode": shortcode,
            "posted_at_timestamp": staged_entry["timestamp"],
            "hashtags": [],
            "music": {},
        }
        if staged_metadata_path is not None and staged_metadata_path.exists():
            sidecar_data = json.loads(staged_metadata_path.read_text(encoding="utf-8"))
            instagram_summary = extract_instagram_summary(
                sidecar_data,
                staged_entry["timestamp"],
                shortcode,
            )

        merged_entry = {
            "rank": rank,
            "timestamp": staged_entry["timestamp"],
            "shortcode": shortcode,
            "paths": {
                "original_video_path": staged_entry["original_video_path"],
                "original_metadata_path": staged_entry.get("original_metadata_path"),
                "staged_video_path": staged_entry["sorted_video_path"],
                "staged_metadata_path": staged_entry.get("sorted_metadata_path"),
                "frame_dir": str(frame_dir),
            },
            "frame_extraction": {
                "mode": "all_frames",
                "frame_pattern": str(frame_dir / "frame_%06d.jpg"),
                "frame_format": "jpg",
                "frame_count": frame_count,
            },
            "ffprobe_summary": ffprobe_summary,
            "instagram_summary": instagram_summary,
            "ffprobe_raw": ffprobe_data,
            "instagram_sidecar_raw": sidecar_data,
        }

        ffprobe_path = ffprobe_root / f"{rank:02d}_{shortcode}.json"
        merged_path = merged_root / f"{rank:02d}_{shortcode}.json"
        ffprobe_path.write_text(json.dumps(ffprobe_data, indent=2) + "\n", encoding="utf-8")
        merged_path.write_text(json.dumps(merged_entry, indent=2) + "\n", encoding="utf-8")

        merged_entry["paths"]["ffprobe_json_path"] = str(ffprobe_path)
        merged_entry["paths"]["merged_json_path"] = str(merged_path)
        batch_entries.append(merged_entry)

    batch_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_staged_dir": str(staged_dir),
        "output_dir": str(output_dir),
        "frame_extraction_mode": "all_frames",
        "videos": batch_entries,
        "summary": build_batch_summary(batch_entries),
    }

    manifest_path = output_dir / "instagram_saved_latest_20_manifest.json"
    manifest_path.write_text(json.dumps(batch_manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract every frame from the staged Instagram saved-video set and "
            "merge ffprobe plus Instagram sidecar metadata into a final JSON manifest."
        )
    )
    parser.add_argument(
        "--staged-dir",
        type=Path,
        default=Path.home() / "Downloads" / "instagram" / "saved_processing" / "latest_20_videos",
        help="Directory created by sort_saved_videos.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path.home()
            / "Downloads"
            / "instagram"
            / "saved_processing"
            / "latest_20_videos_analysis"
        ),
        help="Destination for frames and merged metadata.",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    staged_dir = args.staged_dir.expanduser().resolve()
    output_dir = args.output.expanduser().resolve()

    if not staged_dir.exists():
        raise SystemExit(f"Staged directory does not exist: {staged_dir}")
    if not staged_dir.is_dir():
        raise SystemExit(f"Staged path is not a directory: {staged_dir}")

    manifest_path = process_videos(staged_dir, output_dir)
    print(f"Saved merged manifest to: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
