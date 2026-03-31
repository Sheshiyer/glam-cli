#!/usr/bin/env python3
"""OCR selected high-signal frames and fold results into the saved-video manifest."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'._-]*")
STOPWORDS = {
    "about",
    "activity",
    "all",
    "also",
    "and",
    "are",
    "best",
    "but",
    "click",
    "code",
    "comment",
    "for",
    "free",
    "from",
    "have",
    "here",
    "into",
    "just",
    "like",
    "list",
    "made",
    "make",
    "more",
    "mtok",
    "only",
    "open",
    "over",
    "play",
    "ready",
    "recent",
    "that",
    "the",
    "their",
    "they",
    "them",
    "there",
    "these",
    "this",
    "those",
    "tips",
    "today",
    "used",
    "using",
    "video",
    "videos",
    "welcome",
    "what",
    "when",
    "where",
    "which",
    "will",
    "work",
    "with",
    "you",
    "your",
}


def load_manifest(manifest_path: Path) -> dict:
    """Load the existing batch manifest."""
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def evenly_spaced_frames(frame_paths: list[Path], max_samples: int) -> list[Path]:
    """Return evenly spaced sampled frames from the full frame list."""
    if not frame_paths:
        return []
    if len(frame_paths) <= max_samples:
        return frame_paths

    indices = {
        min(
            len(frame_paths) - 1,
            round(position * (len(frame_paths) - 1) / (max_samples - 1)),
        )
        for position in range(max_samples)
    }
    return [frame_paths[index] for index in sorted(indices)]


def run_tesseract_tsv(image_path: Path) -> str:
    """Run Tesseract TSV OCR over an image."""
    result = subprocess.run(
        [
            "tesseract",
            str(image_path),
            "stdout",
            "--psm",
            "6",
            "tsv",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_tesseract_tsv(tsv_text: str, min_confidence: float) -> dict:
    """Parse TSV OCR output into a scored frame summary."""
    reader = csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
    kept_words: list[str] = []
    confidences: list[float] = []

    for row in reader:
        raw_text = (row.get("text") or "").strip()
        if not raw_text or not WORD_RE.search(raw_text):
            continue

        try:
            confidence = float(row.get("conf") or -1)
        except ValueError:
            confidence = -1
        if confidence < min_confidence:
            continue

        kept_words.append(raw_text)
        confidences.append(confidence)

    text = " ".join(kept_words).strip()
    char_count = len(text)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    score = char_count * (avg_confidence / 100.0)

    return {
        "text": text,
        "char_count": char_count,
        "word_count": len(kept_words),
        "avg_confidence": avg_confidence,
        "score": score,
    }


def normalize_terms(text: str) -> list[str]:
    """Normalize OCR text into useful terms for batch summaries."""
    terms: list[str] = []
    for match in WORD_RE.findall(text.lower()):
        letter_count = sum(character.isalpha() for character in match)
        digit_count = sum(character.isdigit() for character in match)
        if letter_count == 0 or digit_count > letter_count:
            continue
        if len(match) < 3 or match in STOPWORDS:
            continue
        terms.append(match)
    return terms


def select_high_signal_frames(
    frame_dir: Path,
    max_samples: int,
    top_n: int,
    min_confidence: float,
    min_chars: int,
) -> dict:
    """Sample a frame directory, OCR each sample, and return the highest-signal results."""
    all_frames = sorted(frame_dir.glob("frame_*.jpg"))
    sampled_frames = evenly_spaced_frames(all_frames, max_samples)

    sampled_results: list[dict] = []
    for frame_path in sampled_frames:
        tsv_text = run_tesseract_tsv(frame_path)
        ocr_metrics = parse_tesseract_tsv(tsv_text, min_confidence=min_confidence)
        sampled_results.append(
            {
                "frame_path": str(frame_path),
                "frame_name": frame_path.name,
                **ocr_metrics,
            }
        )

    high_signal_frames = [
        result for result in sampled_results if result["char_count"] >= min_chars
    ]
    high_signal_frames.sort(
        key=lambda item: (item["score"], item["char_count"], item["avg_confidence"]),
        reverse=True,
    )

    if not high_signal_frames and sampled_results:
        high_signal_frames = sorted(
            sampled_results,
            key=lambda item: (item["score"], item["char_count"], item["avg_confidence"]),
            reverse=True,
        )[:1]

    selected_frames = high_signal_frames[:top_n]
    concatenated_text = " ".join(frame["text"] for frame in selected_frames if frame["text"])

    return {
        "sampling_strategy": {
            "frame_selection": "evenly_spaced_samples",
            "sampled_frame_count": len(sampled_frames),
            "sample_pool_size": len(all_frames),
            "max_samples": max_samples,
            "selection_metric": "ocr_score = char_count * avg_confidence",
            "min_confidence": min_confidence,
            "min_chars": min_chars,
            "selected_top_n": top_n,
        },
        "selected_frames": selected_frames,
        "selected_frame_count": len(selected_frames),
        "sampled_frame_count": len(sampled_frames),
        "ocr_text_combined": concatenated_text,
        "ocr_term_counts": Counter(normalize_terms(concatenated_text)).most_common(20),
    }


def build_ocr_summary(videos: list[dict]) -> dict:
    """Build batch-level OCR summary from per-video OCR outputs."""
    total_sampled_frames = sum(
        video["ocr_summary"]["sampled_frame_count"] for video in videos
    )
    total_selected_frames = sum(
        video["ocr_summary"]["selected_frame_count"] for video in videos
    )
    videos_with_text = sum(
        1 for video in videos if video["ocr_summary"]["ocr_text_combined"].strip()
    )

    term_counter: Counter[str] = Counter()
    snippet_candidates: list[dict] = []

    for video in videos:
        term_counter.update(dict(video["ocr_summary"]["ocr_term_counts"]))
        for frame in video["ocr_summary"]["selected_frames"]:
            if not frame["text"]:
                continue
            snippet_candidates.append(
                {
                    "rank": video["rank"],
                    "shortcode": video["shortcode"],
                    "frame_name": frame["frame_name"],
                    "score": frame["score"],
                    "text": frame["text"][:200],
                }
            )

    snippet_candidates.sort(key=lambda item: item["score"], reverse=True)

    return {
        "mode": "sampled_high_signal_frames",
        "total_sampled_frames": total_sampled_frames,
        "total_selected_frames": total_selected_frames,
        "videos_with_detected_text": videos_with_text,
        "top_terms": [
            {"term": term, "count": count}
            for term, count in term_counter.most_common(20)
        ],
        "top_snippets": snippet_candidates[:15],
    }


def write_per_video_ocr_json(ocr_dir: Path, video: dict) -> Path:
    """Persist OCR summary for a single video."""
    ocr_dir.mkdir(parents=True, exist_ok=True)
    path = ocr_dir / f"{video['rank']:02d}_{video['shortcode']}.json"
    payload = {
        "rank": video["rank"],
        "shortcode": video["shortcode"],
        "staged_video_path": video["paths"]["staged_video_path"],
        "ocr_summary": video["ocr_summary"],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def update_merged_json(video: dict) -> None:
    """Update the per-video merged JSON file with OCR data."""
    merged_path = Path(video["paths"]["merged_json_path"])
    merged_payload = json.loads(merged_path.read_text(encoding="utf-8"))
    merged_payload["ocr_summary"] = video["ocr_summary"]
    merged_path.write_text(json.dumps(merged_payload, indent=2) + "\n", encoding="utf-8")


def enrich_manifest(
    manifest_path: Path,
    ocr_dir: Path,
    max_samples: int,
    top_n: int,
    min_confidence: float,
    min_chars: int,
) -> dict:
    """Run OCR enrichment over the existing manifest."""
    manifest = load_manifest(manifest_path)

    for video in manifest["videos"]:
        frame_dir = Path(video["paths"]["frame_dir"])
        ocr_summary = select_high_signal_frames(
            frame_dir=frame_dir,
            max_samples=max_samples,
            top_n=top_n,
            min_confidence=min_confidence,
            min_chars=min_chars,
        )
        video["ocr_summary"] = ocr_summary
        ocr_json_path = write_per_video_ocr_json(ocr_dir, video)
        video["paths"]["ocr_json_path"] = str(ocr_json_path)
        update_merged_json(video)
        print(
            f"Processed OCR for rank {video['rank']:02d} "
            f"({video['shortcode']}): {ocr_summary['selected_frame_count']} high-signal frames"
        )

    manifest["summary"]["ocr"] = build_ocr_summary(manifest["videos"])
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Run OCR on sampled high-signal frames from the saved-video analysis output "
            "and fold the results into the manifest."
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
        help="Path to the existing analysis manifest.",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        default=(
            Path.home()
            / "Downloads"
            / "instagram"
            / "saved_processing"
            / "latest_20_videos_analysis"
            / "ocr"
        ),
        help="Directory to write per-video OCR summaries.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=24,
        help="Maximum sampled frames per video to OCR before selecting high-signal frames.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of high-signal OCR frames to keep per video.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=45.0,
        help="Minimum Tesseract word confidence to keep a token.",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=18,
        help="Minimum OCR character count for a frame to be considered high-signal.",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    if args.max_samples <= 0:
        raise SystemExit("--max-samples must be positive")
    if args.top_n <= 0:
        raise SystemExit("--top-n must be positive")

    manifest_path = args.manifest.expanduser().resolve()
    ocr_dir = args.ocr_dir.expanduser().resolve()

    enrich_manifest(
        manifest_path=manifest_path,
        ocr_dir=ocr_dir,
        max_samples=args.max_samples,
        top_n=args.top_n,
        min_confidence=args.min_confidence,
        min_chars=args.min_chars,
    )
    print(f"Updated manifest with OCR enrichment: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
