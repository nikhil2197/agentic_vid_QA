#!/usr/bin/env python3
"""
One-time script to generate a full-day transcript over the 5 videos
listed in config/videos.yaml using the user's transcript prompt.

It uses the same adapters (LLMAdapter for Gemini and CatalogAdapter),
processes videos sequentially, applies retry with exponential backoff,
and writes a text transcript to data/transcripts/transcript_YYYY-MM-DD.txt.
"""

import os
import sys
import time
import logging
from datetime import datetime

from src.adapters.llm_adapter import LLMAdapter
from src.adapters.catalog_adapter import CatalogAdapter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("generate_transcript")

TRANSCRIPT_DIR = os.path.join("data", "transcripts")

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def load_prompt() -> str:
    with open("prompts/transcript_one_time.txt", "r") as f:
        return f.read().strip()

def call_with_retries(llm: LLMAdapter, prompt: str, gcs_uri: str, retries: int = 3, base_sleep: float = 2.0) -> str:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return llm.call_video(prompt=prompt, gcs_uri=gcs_uri)
        except Exception as e:
            last_err = e
            sleep_s = base_sleep * (2 ** (attempt - 1))
            logger.warning(f"Attempt {attempt} failed: {e}. Sleeping {sleep_s:.1f}s before retry...")
            time.sleep(sleep_s)
    raise last_err

def main():
    # Show prompt before running (per user request)
    user_prompt = load_prompt()
    print("\n===== TRANSCRIPT PROMPT (will be used for each video) =====\n")
    print(user_prompt)
    print("\n==========================================================\n")

    # Ask for confirmation
    resp = input("Proceed to generate transcript now? [y/N]: ").strip().lower()
    if resp not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)

    # Initialize adapters: prefer env GOOGLE_CLOUD_PROJECT, else use provided project id
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or "clever-environs-458604-c8"
    llm = LLMAdapter(project_id=project_id)
    catalog = CatalogAdapter()

    ensure_dir(TRANSCRIPT_DIR)
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = os.path.join(TRANSCRIPT_DIR, f"transcript_{date_str}.txt")

    videos = catalog.list_catalog()
    logger.info(f"Found {len(videos)} videos in catalog; generating transcript for all.")

    lines = []
    lines.append(f"Day Transcript - {date_str}")
    lines.append("")

    for idx, video in enumerate(videos, start=1):
        vid = video['id']
        uri = video['gcs_uri']
        meta_header = (
            f"Video {idx}: {vid}\n"
            f"  Session: {video.get('session-type','Unknown')}\n"
            f"  Start: {video.get('start-time','Unknown')}  End: {video.get('end-time','Unknown')}\n"
            f"  Description: {video.get('act-description','No description')}\n"
        )
        print(f"\nAnalyzing {vid} ...")

        # Use the user's prompt verbatim to call the video model
        # Provide per-video metadata context to the model
        context = (
            f"\nContext for this video:\n"
            f"Video ID: {vid}\n"
            f"Session: {video.get('session-type','Unknown')}\n"
            f"Start: {video.get('start-time','Unknown')}  End: {video.get('end-time','Unknown')}\n"
            f"Description: {video.get('act-description','No description')}\n"
        )
        prompt = user_prompt + "\n\n" + context

        try:
            text = call_with_retries(llm, prompt, uri, retries=3, base_sleep=2.0)
        except Exception as e:
            logger.error(f"Failed to analyze {vid}: {e}")
            text = "[ERROR] Could not generate transcript for this video."

        lines.append("=" * 80)
        lines.append(meta_header)
        lines.append(text)
        lines.append("")

        # Friendly pacing between videos
        time.sleep(1.5)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nSaved transcript: {out_path}")

if __name__ == "__main__":
    main()
