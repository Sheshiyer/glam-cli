#!/usr/bin/env python3
"""Run OCR over sampled high-signal frames and fold results into the batch manifest."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

from PIL import Image, ImageOps

WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\\-]{2,}")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "you",
    "your",
    "from",
    "into",
    "are",
    "was",
    "how",
    "all",
    "but",
    "not",
    "use",
    "out",
}


def load_manifest(manifest_path: Path) -> dict:
    """Load the existing analysis manifest."""
    if not manifest_path.exists():
        raise SystemExit(f"Missing manifest: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def select_sample_frames(frame_dir: Path, samples_per_video: int) -> list[Path]:
    """Evenly sample frames across a video's extracted frame directory."""
    frames = sorted(frame_dir.glob("frame_*.jpg"))
    if not frames:
        return []
    if len(frames) <= samples_per_video:
        return frames

    indexes = {
        round(i * (len(frames) - 1) / (samples_per_video - 1))
        for i in range(samples_per_video)
    }
    return [frames[index] for index in sorted(indexes)]


def preprocess_frame(frame_path: Path) -> Path:
    """Prepare a temporary OCR-friendly version of the frame."""
    with Image.open(frame_path) as image:
        grayscale = image.convert("L")
        expanded = grayscale.resize(
            (grayscale.width * 2, grayscale.height * 2),
            Image.Resampling.LANCZOS,
        )
        processed = ImageOps.autocontrast(expanded)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        processed.save(temp_path)
        return temp_path


def parse_tesseract_tsv(tsv_text: str) -> tuple[str, float | None, int, list[str]]:
    """Extract normalized OCR text and confidence from TSV output."""
    words: list[str] = []
    confidences: list[float] = []

    for index, line in enumerate(tsv_text.splitlines()):
        if index == 0 or not line.strip():
            continue
        parts = line.split("\t", maxsplit=11)
        if len(parts) != 12:
            continue

        conf_text = parts[10].strip()
        text = parts[11].strip()
        if not text:
            continue
        words.append(text)
        try:
            confidence = float(conf_text)
        except ValueError:
            confidence = -1
        if confidence >= 0:
            confidences.append(confidence)

    normalized_text = " ".join(words)
    mean_confidence = (
        sum(confidences) / len(confidences) if confidences else None
    )
    return normalized_text, mean_confidence, len(words), words


def frame_number_from_name(frame_path: Path) -> int:
    """Extract the numeric frame index from frame_000123.jpg."""
    match = re.search(r"frame_(\d+)\.jpg$", frame_path.name)
    if match is None:
        return 0
    return int(match.group(1))


def ocr_frame(frame_path: Path, fps: float | None) -> dict:
    """Run OCR for a single frame and return a scored result."""
    temp_path = preprocess_frame(frame_path)
    try:
        result = subprocess.run(
            [
                "tesseract",
                str(temp_path),
                "stdout",
                "--psm",
                "6",
                "-l",
                "eng",
                "tsv",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    text, mean_confidence, word_count, words = parse_tesseract_tsv(result.stdout)
    frame_number = frame_number_from_name(frame_path)
    approx_timestamp_seconds = (
        (frame_number - 1) / fps if fps and frame_number > 0 else None
    )
    keyword_tokens = [word.lower() for word in WORD_RE.findall(text)]
    signal_score = len(text) * ((mean_confidence or 0) / 100 if mean_confidence else 0.5)

    return {
        "frame_name": frame_path.name,
        "frame_path": str(frame_path),
        "frame_number": frame_number,
        "approx_timestamp_seconds": approx_timestamp_seconds,
        "text": text,
        "char_count": len(text),
        "word_count": word_count,
        "mean_confidence": mean_confidence,
        "signal_score": signal_score,
        "keywords": keyword_tokens,
        "raw_words": words,
    }


def summarize_ocr(videos: list[dict]) -> dict:
    """Build batch-level OCR summary data."""
    sampled_results = [
        result
        for video in videos
        for result in video.get("ocr", {}).get("sampled_results", [])
    ]
    selected_hits = [
        hit
        for video in videos
        for hit in video.get("ocr", {}).get("selected_high_signal_frames", [])
    ]
    keyword_counter = Counter(
        keyword
        for hit in selected_hits
        for keyword in hit.get("keywords", [])
        if keyword not in STOPWORDS
    )

    return {
        "videos_with_ocr_hits": sum(
            1 for video in videos if video.get("ocr", {}).get("selected_high_signal_frames")
        ),
        "total_sampled_frames": len(sampled_results),
        "total_high_signal_frames": len(selected_hits),
        "top_ocr_keywords": [
            {"keyword": keyword, "count": count}
            for keyword, count in keyword_counter.most_common(20)
        ],
        "best_hits": sorted(
            [
                {
                    "rank": video["rank"],
                    "shortcode": video["shortcode"],
                    "frame_name": hit["frame_name"],
                    "char_count": hit["char_count"],
                    "mean_confidence": hit["mean_confidence"],
                    "text": hit["text"][:200],
                }
                for video in videos
                for hit in video.get("ocr", {}).get("selected_high_signal_frames", [])
            ],
            key=lambda item: (
                item["char_count"],
                item["mean_confidence"] or 0,
            ),
            reverse=True,
        )[:20],
    }


def enrich_manifest(
    manifest_path: Path,
    samples_per_video: int,
    top_hits_per_video: int,
    min_char_count: int,
    workers: int,
) -> Path:
    """Run OCR enrichment and overwrite the manifest with OCR data."""
    manifest = load_manifest(manifest_path)
    videos = manifest.get("videos", [])
    if not videos:
        raise SystemExit("Manifest has no videos to enrich")

    ocr_root = manifest_path.parent / "ocr"
    if ocr_root.exists():
        shutil.rmtree(ocr_root)
    ocr_root.mkdir(parents=True, exist_ok=True)

    backup_path = manifest_path.with_name(f"{manifest_path.stem}.pre_ocr.json")
    if not backup_path.exists():
        shutil.copy2(manifest_path, backup_path)

    for video in videos:
        frame_dir = Path(video["paths"]["frame_dir"])
        samples = select_sample_frames(frame_dir, samples_per_video)
        fps = video.get("ffprobe_summary", {}).get("fps")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            sampled_results = list(
                executor.map(partial(ocr_frame, fps=fps), samples)
            )

        sampled_results.sort(
            key=lambda item: (item["signal_score"], item["char_count"]),
            reverse=True,
        )
        selected_hits = [
            result
            for result in sampled_results
            if result["char_count"] >= min_char_count
        ][:top_hits_per_video]

        ocr_payload = {
            "sampling_strategy": {
                "samples_per_video": samples_per_video,
                "top_hits_per_video": top_hits_per_video,
                "min_char_count": min_char_count,
                "tesseract_lang": "eng",
                "psm": 6,
            },
            "sampled_results": sampled_results,
            "selected_high_signal_frames": selected_hits,
            "best_text": selected_hits[0]["text"] if selected_hits else "",
        }

        video["ocr"] = ocr_payload

        merged_path = Path(video["paths"]["merged_json_path"])
        merged_json = json.loads(merged_path.read_text(encoding="utf-8"))
        merged_json["ocr"] = ocr_payload
        merged_path.write_text(json.dumps(merged_json, indent=2) + "\n", encoding="utf-8")

        ocr_path = ocr_root / f"{video['rank']:02d}_{video['shortcode']}.json"
        ocr_path.write_text(json.dumps(ocr_payload, indent=2) + "\n", encoding="utf-8")
        video["paths"]["ocr_json_path"] = str(ocr_path)

    manifest["ocr_enrichment"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sampling_strategy": {
            "samples_per_video": samples_per_video,
            "top_hits_per_video": top_hits_per_video,
            "min_char_count": min_char_count,
            "workers": workers,
            "tesseract_lang": "eng",
            "psm": 6,
        },
        "summary": summarize_ocr(videos),
    }

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Run OCR over sampled high-signal frames from the Instagram saved-video "
            "analysis batch and fold the results into the manifest."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=(
            Path.home()
            / "Downloads"
            / "instagram"
            / "saved_processing"
            / "latest_20_videos_analysis"
            / "instagram_saved_latest_20_manifest.json"
        ),
        help="Existing analysis manifest to enrich.",
    )
    parser.add_argument(
        "--samples-per-video",
        type=int,
        default=12,
        help="Number of evenly spaced frames to OCR per video.",
    )
    parser.add_argument(
        "--top-hits-per-video",
        type=int,
        default=5,
        help="How many OCR hits to keep per video after scoring.",
    )
    parser.add_argument(
        "--min-char-count",
        type=int,
        default=12,
        help="Minimum OCR character count for a frame to count as high-signal.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel OCR worker count.",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    if args.samples_per_video <= 0:
        raise SystemExit("--samples-per-video must be positive")
    if args.top_hits_per_video <= 0:
        raise SystemExit("--top-hits-per-video must be positive")
    if args.min_char_count < 0:
        raise SystemExit("--min-char-count must be non-negative")
    if args.workers <= 0:
        raise SystemExit("--workers must be positive")

    manifest_path = args.manifest.expanduser().resolve()
    enriched_manifest = enrich_manifest(
        manifest_path=manifest_path,
        samples_per_video=args.samples_per_video,
        top_hits_per_video=args.top_hits_per_video,
        min_char_count=args.min_char_count,
        workers=args.workers,
    )
    print(f"OCR-enriched manifest saved to: {enriched_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
