import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


BASE_DIR = Path("data") / "child_transcripts"


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_child_transcripts_for_today(child_name: str, date_str: Optional[str] = None) -> Optional[Dict]:
    """Load per-video child transcripts for the given date, assuming a single child folder exists.
    Strategy:
    - Look under data/child_transcripts/by_image/<date>/
    - If multiple subfolders, prefer one whose name contains the child_name (case-insensitive)
      otherwise pick the first deterministically.
    - Read all *.json files inside as per-video payloads and return a combined dict.
    Returns None if nothing found.
    """
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    by_image_dir = BASE_DIR / "by_image" / date_str
    if not by_image_dir.exists():
        return None
    subdirs = [p for p in by_image_dir.iterdir() if p.is_dir()]
    if not subdirs:
        return None
    # Pick matching folder by child name
    chosen = None
    lower_name = (child_name or "").lower()
    for d in subdirs:
        if lower_name and lower_name in d.name.lower():
            chosen = d
            break
    if chosen is None:
        # fallback to first sorted
        chosen = sorted(subdirs, key=lambda p: p.name)[0]

    videos: List[Dict] = []
    for vid_dir_entry in chosen.iterdir():
        # Support layout where JSON files are directly in the chosen folder (vid.json)
        if vid_dir_entry.is_file() and vid_dir_entry.suffix == ".json":
            try:
                videos.append(_read_json(vid_dir_entry))
            except Exception:
                continue
        elif vid_dir_entry.is_dir():
            # Or nested structure: <video_id>/<child>.json
            for file in vid_dir_entry.glob("*.json"):
                try:
                    videos.append(_read_json(file))
                except Exception:
                    continue

    if not videos:
        return None
    return {
        "date": date_str,
        "child": child_name,
        "videos": videos,
        "source_path": str(chosen)
    }

