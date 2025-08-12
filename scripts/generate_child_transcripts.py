#!/usr/bin/env python3
"""
Generate per-child transcripts per video for the current day (simplified features).

Flow:
- Parse the existing day TEXT transcript (data/transcripts/transcript_YYYY-MM-DD.txt).
- For EACH video, take the identified children (outfit labels) from the transcript.
- For EACH (video, child_label), run a simplified child analyzer visually on that video only.
- Output a SINGLE JSON file per (video, child_label): participated (bool), distress_present (bool) + distress_time, short summary.
- Write files to data/child_transcripts/YYYY-MM-DD/<video_id>/<child-slug>.json (replacing existing for today).

Notes:
- Uses the same adapters (LLMAdapter + CatalogAdapter) as the main system.
- Requires access to referenced GCS URIs and a configured Google Cloud project.
"""

import os
import re
import json
import time
import logging
from datetime import datetime
import argparse
import shutil
from pathlib import Path
from difflib import SequenceMatcher

from src.adapters.llm_adapter import LLMAdapter
from src.adapters.catalog_adapter import CatalogAdapter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("generate_child_transcripts")

TRANSCRIPT_DIR = Path("data") / "transcripts"
CHILD_DIR = Path("data") / "child_transcripts"


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def load_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_prompt(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def normalize_label(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def slugify(s: str) -> str:
    s = normalize_label(s)
    s = s.replace(" ", "-")
    s = re.sub(r"-+", "-", s)
    return s


def fuzzy_group_labels(labels: list[str], threshold: float = 0.6) -> dict[str, str]:
    """Group similar outfit labels and return mapping original -> canonical.
    Uses simple SequenceMatcher on normalized strings.
    Canonical is first-seen representative for its group.
    """
    canonical_list: list[str] = []
    mapping: dict[str, str] = {}

    for lab in labels:
        n = normalize_label(lab)
        if not n:
            continue
        if not canonical_list:
            canonical_list.append(n)
            mapping[lab] = n
            continue
        best = None
        best_score = 0.0
        for c in canonical_list:
            score = SequenceMatcher(a=n, b=c).ratio()
            if score > best_score:
                best = c
                best_score = score
        if best is not None and best_score >= threshold:
            mapping[lab] = best
        else:
            canonical_list.append(n)
            mapping[lab] = n
    return mapping


def call_with_retries_video(llm: LLMAdapter, prompt: str, gcs_uri: str, retries: int = 3, base_sleep: float = 2.0) -> str:
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


def find_latest_day_text_transcript(date_str: str | None = None) -> Path | None:
    ensure_dir(TRANSCRIPT_DIR)
    candidates = sorted(TRANSCRIPT_DIR.glob("transcript_*.txt"))
    if date_str:
        p = TRANSCRIPT_DIR / f"transcript_{date_str}.txt"
        return p if p.exists() else None
    return candidates[-1] if candidates else None


def parse_day_text_transcript(path: Path) -> list[dict]:
    """Parse the day text transcript into a list of sections: [{video_id, students:[...]}, ...].
    Looks for lines 'Video X: <id>' and 'Students:' followed by a line of comma-separated items or inline list.
    """
    text = load_text(path)
    sections = []
    # Split by separators
    blocks = re.split(r"\n=+\n", text)
    for block in blocks:
        m_vid = re.search(r"Video\s+\d+:\s*(?P<vid>[\w-]+)", block)
        if not m_vid:
            continue
        vid = m_vid.group("vid").strip()
        # Find Students section
        students = []
        # Pattern 1: 'Students:' on its own line, next non-empty line contains comma-separated list
        m_students_block = re.search(r"Students:\s*\n(?P<line>[^\n]+)", block, flags=re.IGNORECASE)
        if m_students_block:
            line = m_students_block.group("line").strip()
            # Handle 'No students are present.'
            if not re.search(r"no\s+students\s+are\s+present", line, flags=re.IGNORECASE):
                students = [s.strip() for s in line.split(",") if s.strip()]
        else:
            # Pattern 2: inline 'Students: <comma-separated>'
            m_students_inline = re.search(r"Students:\s*(?P<list>[^\n\.]+)", block, flags=re.IGNORECASE)
            if m_students_inline:
                items = m_students_inline.group("list").strip()
                if not re.search(r"No\s+students\s+are\s+present", items, flags=re.IGNORECASE):
                    students = [s.strip() for s in items.split(",") if s.strip()]
        sections.append({"video_id": vid, "students": students})
    return sections


def extract_children_from_day_json(day_json: dict) -> tuple[list[str], dict[str, list[str]]]:
    """Return (all_labels, label_to_video_ids where observed). Uses raw labels as keys.
    """
    labels: list[str] = []
    label_to_videos: dict[str, list[str]] = {}
    for vid, section in (day_json.get("videos") or {}).items():
        for student in section.get("students", []) or []:
            label = student.get("clothes") or ""
            if not label:
                continue
            labels.append(label)
            label_to_videos.setdefault(label, []).append(vid)
    return labels, label_to_videos


def build_per_video_child_list(sections: list[dict]) -> list[dict]:
    """Return list of {video_id, child_label, slug} keeping labels as-is per video (no cross-video merge)."""
    items = []
    for sec in sections:
        vid = sec["video_id"]
        for lab in sec.get("students", []):
            nlab = normalize_label(lab)
            if not nlab:
                continue
            items.append({
                "video_id": vid,
                "child_label": nlab,
                "slug": slugify(nlab)
            })
    return items


def analyze_child_in_video(llm: LLMAdapter, child_label: str, video_meta: dict) -> dict:
    """Call the simplified child analyzer prompt for one child+video pair and return parsed JSON (dict)."""
    with open("prompts/child_simple_analyzer.txt", "r", encoding="utf-8") as f:
        template = f.read()

    context = (
        f"\nChild outfit: {child_label}\n"
        f"Video ID: {video_meta['id']}\n"
        f"Session: {video_meta.get('session-type','Unknown')}\n"
        f"Start: {video_meta.get('start-time','Unknown')}  End: {video_meta.get('end-time','Unknown')}\n"
        f"Description: {video_meta.get('act-description','No description')}\n"
    )
    prompt = template + "\n\n" + context
    uri = video_meta["gcs_uri"]

    text = call_with_retries_video(llm, prompt, uri, retries=3, base_sleep=2.0)
    try:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("Child analyzer did not return a JSON object")
        # Normalize minimal fields
        payload.setdefault("video_id", video_meta["id"])
        payload.setdefault("child_label", child_label)
        payload.setdefault("participated", False)
        payload.setdefault("distress_present", False)
        payload.setdefault("distress_time", "")
        payload.setdefault("summary", "")
        return payload
    except Exception as e:
        logger.warning(f"Child analyzer not JSON for {video_meta['id']}: {e}")
        return {
            "video_id": video_meta["id"],
            "child_label": child_label,
            "participated": False,
            "distress_present": False,
            "distress_time": "",
            "summary": "Child not confidently observed."
        }


def main():
    parser = argparse.ArgumentParser(description="Generate per-child transcripts (simplified)")
    parser.add_argument("--transcript", help="Path to day text transcript (transcript_YYYY-MM-DD.txt)")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD) used for output folder")
    parser.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")
    args = parser.parse_args()

    # Identify transcript path
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    if args.transcript:
        tpath = Path(args.transcript)
    else:
        tpath = find_latest_day_text_transcript(date_str)
    if not tpath or not tpath.exists():
        print(f"Day text transcript not found for date {date_str}. Aborting.")
        return

    print("\n===== Generate Per-Child Transcripts (simplified) =====\n")
    print(f"Using transcript: {tpath}")
    if not args.confirm:
        resp = input("Proceed now? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborted.")
            return

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or "clever-environs-458604-c8"
    llm = LLMAdapter(project_id=project_id)
    catalog = CatalogAdapter()

    # Parse children per video from text
    sections = parse_day_text_transcript(tpath)
    per_video_children = build_per_video_child_list(sections)
    if not per_video_children:
        print("No children found in day transcript. Nothing to do.")
        return

    # Prepare output dir (delete existing for today)
    out_root = CHILD_DIR / date_str
    if out_root.exists():
        shutil.rmtree(out_root, ignore_errors=True)
    ensure_dir(out_root)

    videos_by_id = {v["id"]: v for v in catalog.list_catalog()}
    outputs = []
    for item in per_video_children:
        vid = item["video_id"]
        label = item["child_label"]
        slug = item["slug"]
        meta = videos_by_id.get(vid)
        if not meta:
            logger.warning(f"Video id {vid} not found in catalog; skipping child {label}")
            continue
        try:
            payload = analyze_child_in_video(llm, label, meta)
        except Exception as e:
            logger.error(f"Failed child analysis {label} in {vid}: {e}")
            payload = {
                "video_id": vid,
                "child_label": label,
                "participated": False,
                "distress_present": False,
                "distress_time": "",
                "summary": "Error analyzing this video."
            }

        out_dir = out_root / vid
        ensure_dir(out_dir)
        out_path = out_dir / f"{slug}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        outputs.append(out_path)
        logger.info(f"Saved child transcript: {out_path}")
        time.sleep(0.2)

    print("\nGenerated per-video child transcripts:")
    for p in outputs:
        print(f" - {p}")
    print("\nDone.")


if __name__ == "__main__":
    main()
