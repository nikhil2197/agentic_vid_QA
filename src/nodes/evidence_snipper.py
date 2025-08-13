import logging
import os
from datetime import datetime
from typing import List, Optional

from src.state import QAState
from src.adapters.catalog_adapter import CatalogAdapter
from src.utils.child_transcript_loader import load_child_transcripts_for_today
from scripts.snip_evidence import snip_evidence_for_video


logger = logging.getLogger(__name__)


def _latest_followup_text(state: QAState) -> Optional[str]:
    if not getattr(state, 'conversation_history', None):
        return None
    for msg in reversed(state.conversation_history):
        role = getattr(msg, 'role', '')
        if role == 'user':
            return getattr(msg, 'content', None)
    return None


def _get_child_name_from_state(state: QAState) -> Optional[str]:
    info = (getattr(state, 'child_info', '') or '').lower()
    if 'ayaan' in info:
        return 'Ayaan'
    if getattr(state, 'demo_mode', False):
        return 'Ayaan'
    return None


def _collect_evidence_times_for_vid2(state: QAState) -> List[str]:
    # Prefer state.child_transcript_data if present
    data = getattr(state, 'child_transcript_data', None)
    if data and isinstance(data, dict):
        items = data.get('videos') or []
        for v in items:
            if (v or {}).get('video_id') == 'vid_2':
                et = v.get('evidence_times') or []
                if isinstance(et, list):
                    return [str(x) for x in et]
                return []

    # Fallback: attempt to load today's child transcript from disk
    child_name = _get_child_name_from_state(state) or ''
    date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        loaded = load_child_transcripts_for_today(child_name, date_str)
        if loaded and isinstance(loaded, dict):
            items = loaded.get('videos') or []
            for v in items:
                if (v or {}).get('video_id') == 'vid_2':
                    et = v.get('evidence_times') or []
                    if isinstance(et, list):
                        return [str(x) for x in et]
    except Exception as e:
        logger.warning(f"evidence_snipper: failed to load child transcripts: {e}")

    return []


    # Removed wall-clock conversion; evidence times are MM:SS offsets


def run(state: QAState, catalog_adapter: CatalogAdapter) -> QAState:
    """
    Node: evidence_snipper
    Behavior: Find evidence_times for vid_2, download from GCS, snip per range, store under data/snippedvideos.
    Output: state.evidence_clips, state.evidence_message
    """
    try:
        # Resolve GCS URI for vid_2
        gcs_uri = catalog_adapter.get_uri('vid_2')

        # Collect evidence times
        evidence_times = _collect_evidence_times_for_vid2(state)
        if not evidence_times:
            state.evidence_message = "No evidence_times found for vid_2."
            state.evidence_clips = {"vid_2": []}
            return state

        # Snip using MM:SS offsets from start of video
        clips = snip_evidence_for_video(
            video_id='vid_2',
            evidence_times=evidence_times,
            gcs_uri=gcs_uri,
            window_seconds_for_point=10,
        )
        state.evidence_clips = {"vid_2": clips}
        if clips:
            state.evidence_message = f"Saved {len(clips)} clip(s) to data/snippedvideos."
        else:
            state.evidence_message = "No clips were produced. Check ffmpeg/gcloud availability."
        return state
    except Exception as e:
        logger.error(f"evidence_snipper failed: {e}")
        state.evidence_message = f"Evidence snipping failed: {e}"
        state.evidence_clips = {"vid_2": []}
        return state
