#!/usr/bin/env python3
"""
Generate per-video child transcripts by following a reference IMAGE of the child.

Usage:
  python -m scripts.generate_child_from_image --image /path/to/child.jpg --date 2025-08-12 --confirm

Behavior:
- Iterates all videos from config/videos.yaml
- For each video, calls Gemini with: [prompt, IMAGE(bytes), VIDEO(GCS)]
- Writes one JSON per (video) under data/child_transcripts/by_image/YYYY-MM-DD/<image-slug>/<video_id>.json

Output JSON (per video):
{
  "video_id": "vid_X",
  "participated": true|false,
  "distress_present": true|false,
  "distress_time": "" | "~MM:SS" | "HH:MM–HH:MM",
  "summary": "≤ 35 words"
}
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime
import argparse

from src.adapters.llm_adapter import LLMAdapter
from src.adapters.catalog_adapter import CatalogAdapter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("generate_child_from_image")

OUT_ROOT = Path("data") / "child_transcripts" / "by_image"


def slugify_filename(path: Path) -> str:
    base = path.stem.lower()
    base = re.sub(r"[^a-z0-9\-_.]+", "-", base)
    base = re.sub(r"-+", "-", base).strip("-")
    return base or "child"


def load_prompt() -> str:
    """Load the unified child mood analyzer prompt used for image-guided transcripts."""
    with open("prompts/child_mood_analyzer.txt", "r", encoding="utf-8") as f:
        return f.read().strip()


def call_with_retries(llm: LLMAdapter, prompt: str, gcs_uri: str, image_path: str, retries: int = 3, base_sleep: float = 2.0) -> str:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return llm.call_video_with_image(prompt=prompt, gcs_uri=gcs_uri, image_path=image_path)
        except Exception as e:
            last_err = e
            sleep_s = base_sleep * (2 ** (attempt - 1))
            logger.warning(f"Attempt {attempt} failed: {e}. Sleeping {sleep_s:.1f}s before retry...")
            time.sleep(sleep_s)
    raise last_err


def main():
    parser = argparse.ArgumentParser(description="Generate per-video child transcripts from a reference image")
    parser.add_argument("--image", required=True, help="Path to the child's reference image (jpg/png)")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD) used for output folder; default: today")
    parser.add_argument("--confirm", action="store_true", help="Skip interactive confirmation prompt")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    out_dir = OUT_ROOT / date_str / slugify_filename(image_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n===== Generate Per-Video Child Transcripts (Image-guided) =====\n")
    print(f"Reference image: {image_path}")
    print(f"Output folder:   {out_dir}")
    if not args.confirm:
        resp = input("Proceed now? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborted.")
            return

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or "clever-environs-458604-c8"
    llm = LLMAdapter(project_id=project_id)
    catalog = CatalogAdapter()

    prompt = load_prompt()
    videos = catalog.list_catalog()
    outputs = []
    for video in videos:
        vid = video["id"]
        uri = video["gcs_uri"]

        context = (
            f"\nVideo ID: {vid}\n"
            f"Session: {video.get('session-type','Unknown')}\n"
            f"Start: {video.get('start-time','Unknown')}  End: {video.get('end-time','Unknown')}\n"
            f"Description: {video.get('act-description','No description')}\n"
        )

        try:
            text = call_with_retries(llm, prompt + "\n\n" + context, uri, str(image_path), retries=3, base_sleep=2.0)
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError("Response is not a JSON object")
            # Ensure the expected fields from child_mood_analyzer are present
            payload.setdefault("video_id", vid)
            payload.setdefault("child_label", "")
            payload.setdefault("observed", False)
            payload.setdefault("engagement_level", "unknown")
            payload.setdefault("mood", [])
            payload.setdefault("behaviors", [])
            payload.setdefault("distress_events", [])
            payload.setdefault("evidence_times", [])
            payload.setdefault("short_per_video_summary", "")
        except Exception as e:
            logger.warning(f"Non-JSON or error for {vid}: {e}")
            # Fallback to a valid schema matching child_mood_analyzer
            payload = {
                "video_id": vid,
                "child_label": "",
                "observed": False,
                "engagement_level": "unknown",
                "mood": [],
                "behaviors": [],
                "distress_events": [],
                "evidence_times": [],
                "short_per_video_summary": "Child not confidently observed."
            }

        out_path = out_dir / f"{vid}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        outputs.append(out_path)
        logger.info(f"Saved: {out_path}")
        time.sleep(0.3)

    print("\nGenerated per-video child transcripts (image-guided):")
    for p in outputs:
        print(f" - {p}")
    print("\nDone.")


if __name__ == "__main__":
    main()
