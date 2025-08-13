import json
import os
from datetime import datetime
import logging
from typing import Dict

from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter
from src.adapters.catalog_adapter import CatalogAdapter
from src.utils.child_transcript_loader import load_child_transcripts_for_today

logger = logging.getLogger(__name__)

TRANSCRIPT_DIR = os.path.join("data", "transcripts")

def _ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        # Directory may already exist or be created by another process
        pass

def _load_prompt() -> str:
    with open("prompts/transcript_full_day.txt", "r") as f:
        return f.read()

def _build_section_for_video(
    video_id: str,
    state: QAState,
    llm: LLMAdapter,
    catalog: CatalogAdapter,
) -> Dict:
    meta = catalog.get_metadata(video_id)
    gcs_uri = meta.get("gcs_uri")
    prompt_template = _load_prompt()
    # Provide light metadata context to the model
    meta_ctx = (
        f"\nVideo ID: {video_id}\n"
        f"Session: {meta.get('session-type', 'Unknown')}\n"
        f"Start: {meta.get('start-time', 'Unknown')}  End: {meta.get('end-time', 'Unknown')}\n"
        f"Description: {meta.get('act-description', 'No description')}\n"
    )
    prompt = prompt_template + "\n\n" + meta_ctx
    text = llm.call_video(prompt=prompt, gcs_uri=gcs_uri)
    try:
        section = json.loads(text)
        return section
    except Exception as e:
        logger.warning(f"Transcript section not JSON for {video_id}; storing fallback text. Error: {e}")
        return {"activity": text[:200], "skills": [], "students": [], "distress_events": [], "evidence_times": []}

def run(state: QAState, llm_adapter: LLMAdapter, catalog_adapter: CatalogAdapter) -> QAState:
    """
    Node: transcript_builder
    Input: target_videos (from picker)
    Output: transcript_path (JSON file for the day combining per-video sections)
    """
    start_ts = __import__('time').time()

    try:
        # Demo transcripts-only shortcut: force use of cached demo files and avoid model calls
        if getattr(state, 'demo_mode', False) and getattr(state, 'transcripts_only', False):
            demo_txt = os.path.join(TRANSCRIPT_DIR, "transcript_2025-08-12.txt")
            if os.path.exists(demo_txt):
                state.transcript_path = demo_txt
                # Prefer transcript in this mode
                state.transcript_prefer = True
                # Attempt to load child-specific transcripts for the same demo date
                try:
                    child_info_str = (getattr(state, 'child_info', '') or '').lower()
                    if 'ayaan' in child_info_str:
                        child_data = load_child_transcripts_for_today('Ayaan', '2025-08-12')
                        if child_data:
                            state.child_transcript_data = child_data
                            logger.info("transcript_builder: demo mode loaded child transcript data for Ayaan (2025-08-12)")
                except Exception as e:
                    logger.warning(f"transcript_builder: demo child transcript load skipped due to error: {e}")
                duration_ms = int((__import__('time').time() - start_ts) * 1000)
                logger.info(f"transcript_builder: demo transcripts-only using cached {demo_txt} in {duration_ms}ms")
                return state
            else:
                logger.warning("transcript_builder: demo transcripts-only requested but demo transcript file not found; proceeding with normal logic")

        if not state.target_videos:
            logger.info("transcript_builder: no target_videos; skipping")
            return state

        _ensure_dir(TRANSCRIPT_DIR)
        date_str = datetime.now().strftime("%Y-%m-%d")
        json_out_path = os.path.join(TRANSCRIPT_DIR, f"transcript_{date_str}.json")

        # Prefer a pre-generated text transcript if present; else reuse today's JSON if exists
        try:
            candidates = [
                os.path.join(TRANSCRIPT_DIR, fn)
                for fn in os.listdir(TRANSCRIPT_DIR)
                if fn.startswith("transcript_") and (fn.endswith(".txt") or fn.endswith(".json"))
            ]
            latest = max(candidates, key=lambda p: os.path.getmtime(p)) if candidates else None
        except Exception:
            latest = None

        if latest and latest.endswith(".txt"):
            state.transcript_path = latest
            duration_ms = int((__import__('time').time() - start_ts) * 1000)
            logger.info(f"transcript_builder: using existing text transcript at {latest} in {duration_ms}ms")
            return state
        if os.path.exists(json_out_path):
            state.transcript_path = json_out_path
            duration_ms = int((__import__('time').time() - start_ts) * 1000)
            logger.info(f"transcript_builder: reused cached transcript at {json_out_path} in {duration_ms}ms")
            # Try to load child-specific transcripts if child is Ayaan
            try:
                child_info_str = (getattr(state, 'child_info', '') or '').lower()
                if 'ayaan' in child_info_str:
                    child_data = load_child_transcripts_for_today('Ayaan', date_str)
                    if child_data:
                        state.child_transcript_data = child_data
                        state.transcript_prefer = True
                        logger.info("transcript_builder: loaded child transcript data for Ayaan and set prefer=true")
            except Exception as e:
                logger.warning(f"transcript_builder: child transcript load skipped due to error: {e}")
            return state

        # Build per-video sections
        transcript = {
            "date": date_str,
            "videos": {},
            "meta": {"prompt_version": state.transcript_prompt_version or "v1"}
        }
        for vid in state.target_videos:
            try:
                section = _build_section_for_video(vid, state, llm_adapter, catalog_adapter)
                transcript["videos"][vid] = section
            except Exception as e:
                logger.error(f"transcript_builder: failed for {vid}: {e}")
                transcript["videos"][vid] = {"activity": "", "skills": [], "students": [], "distress_events": [], "evidence_times": []}

        # Persist JSON
        try:
            with open(json_out_path, "w") as f:
                json.dump(transcript, f, ensure_ascii=False, separators=(",", ":"))
            state.transcript_path = json_out_path
        except Exception as e:
            logger.error(f"transcript_builder: failed to write transcript {out_path}: {e}")

        duration_ms = int((__import__('time').time() - start_ts) * 1000)
        logger.info(f"transcript_builder completed in {duration_ms}ms, output: {state.transcript_path}")
        # After building, also attempt to load child transcript for Ayaan if applicable
        try:
            child_info_str = (getattr(state, 'child_info', '') or '').lower()
            if 'ayaan' in child_info_str:
                child_data = load_child_transcripts_for_today('Ayaan', date_str)
                if child_data:
                    state.child_transcript_data = child_data
                    state.transcript_prefer = True
                    logger.info("transcript_builder: loaded child transcript data for Ayaan and set prefer=true")
        except Exception as e:
            logger.warning(f"transcript_builder: child transcript load skipped due to error: {e}")
        return state

    except Exception as e:
        logger.error(f"transcript_builder failed: {e}")
        return state
