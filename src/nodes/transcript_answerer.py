import json
import logging
from typing import Any, Dict

from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

def run(state: QAState, llm_adapter: LLMAdapter) -> QAState:
    """
    Node: transcript_answerer
    Input: target_question, transcript_path
    Output: transcript_can_answer, transcript_answer (and possibly per_video_answers for composer)
    """
    start_ts = __import__('time').time()
    try:
        # If child-specific transcript data is present (e.g., for Ayaan), combine with day transcript when available
        if getattr(state, 'child_transcript_data', None):
            # Strict field mapping for child questions
            def _infer_fields(q: str) -> set:
                ql = (q or "").lower()
                fields = set()
                if any(k in ql for k in ["mood", "feeling", "affect", "emotional", "emotion", "demeanor"]):
                    fields.add("mood")
                if any(k in ql for k in ["engage", "engagement", "attention", "focused", "focus"]):
                    fields.add("engagement_level")
                if any(k in ql for k in ["behav", "action", "participat", "join", "do", "did"]):
                    fields.add("behaviors")
                    fields.add("participated")
                if any(k in ql for k in ["distress", "cry", "upset", "frustrat", "meltdown", "tear", "sad", "anxious"]):
                    fields.add("distress_events")
                return fields

            requested = _infer_fields(getattr(state, 'target_question', None) or state.user_question)
            # Build filtered child evidence by requested fields
            filtered = {"videos": []}
            for v in (state.child_transcript_data.get("videos") or []):
                entry = {"video_id": v.get("video_id")}
                if "mood" in requested and v.get("mood"):
                    entry["mood"] = v.get("mood")
                if "engagement_level" in requested and v.get("engagement_level"):
                    entry["engagement_level"] = v.get("engagement_level")
                if "participated" in requested and (v.get("participated") is not None):
                    entry["participated"] = v.get("participated")
                if "behaviors" in requested and v.get("behaviors"):
                    entry["behaviors"] = v.get("behaviors")
                if "distress_events" in requested and v.get("distress_events") is not None:
                    entry["distress_events"] = v.get("distress_events")
                # always helpful summary if present
                if v.get("short_per_video_summary"):
                    entry["summary"] = v.get("short_per_video_summary")
                # include evidence_times to ground
                if v.get("evidence_times"):
                    entry["evidence_times"] = v.get("evidence_times")
                # keep only if we have any field besides video_id
                if len(entry) > 1:
                    filtered["videos"].append(entry)

            if filtered["videos"]:
                # Provide filtered child evidence (strict) + optional day context to composer
                day_label = None
                day_content = None
                if getattr(state, 'transcript_path', None):
                    try:
                        with open(state.transcript_path, "r", encoding="utf-8") as f:
                            raw = f.read()
                        try:
                            _obj = json.loads(raw)
                            day_content = json.dumps(_obj, ensure_ascii=False, separators=(",", ":"))
                            day_label = "Day Transcript JSON"
                        except Exception:
                            day_content = raw
                            day_label = "Day Transcript (text)"
                    except Exception:
                        pass

                evidence_map = {"child_transcript": json.dumps(filtered, ensure_ascii=False, separators=(",", ":"))}
                if day_content:
                    evidence_map["day_transcript"] = day_content
                state.per_video_answers = evidence_map
                state.transcript_can_answer = True
                state.used_transcript = True
                logger.info("transcript_answerer: using strict child evidence fields with day context")
                return state

            # Fallback to LLM gating if strict fields not detected or empty
            with open("prompts/child_transcript_answerer.txt", "r") as f:
                template = f.read()

            child_context = ""
            if getattr(state, 'child_info', None):
                child_context = f"\nChild information: {state.child_info}"

            child_json_str = json.dumps(state.child_transcript_data, ensure_ascii=False, separators=(",", ":"))

            day_label = None
            day_content = None
            if getattr(state, 'transcript_path', None):
                try:
                    with open(state.transcript_path, "r", encoding="utf-8") as f:
                        raw = f.read()
                    # Try JSON parse; else treat as text
                    try:
                        _obj = json.loads(raw)
                        day_content = json.dumps(_obj, ensure_ascii=False, separators=(",", ":"))
                        day_label = "Day Transcript JSON"
                    except Exception:
                        day_content = raw
                        day_label = "Day Transcript (text)"
                except Exception:
                    pass

            prompt = f"{template}\n\nRefined question: {state.target_question}{child_context}\n\nChild Transcript JSON:\n{child_json_str}\n"
            if day_content:
                prompt += f"\n{day_label}:\n{day_content}\n"

            result = llm_adapter.call_json(prompt, temperature=0.0)
            can_answer_flag = bool(result.get("can_answer", False))
            confidence = float(result.get("confidence", 0.0))
            can_answer = can_answer_flag and (confidence >= 0.5)
            state.transcript_can_answer = can_answer
            if can_answer:
                evidence = {"child_transcript": child_json_str}
                if day_content:
                    evidence["day_transcript"] = day_content
                state.per_video_answers = evidence
                state.used_transcript = True
                logger.info("transcript_answerer: prepared child+day transcript evidence for composer")
                return state

        if not state.transcript_path:
            logger.info("transcript_answerer: no transcript available; skipping")
            return state

        # Read transcript file; support JSON or text
        is_json = state.transcript_path.endswith('.json')
        transcript_payload = None
        with open(state.transcript_path, "r", encoding="utf-8") as f:
            content = f.read()
            if is_json:
                try:
                    transcript_payload = json.loads(content)
                except Exception:
                    is_json = False  # fallback to text embedding if JSON parse fails
            if not is_json:
                transcript_payload = content

        # Build prompt
        with open("prompts/transcript_answerer.txt", "r") as f:
            template = f.read()

        child_context = ""
        if getattr(state, 'child_info', None):
            child_context = f"\nChild information: {state.child_info}"

        if is_json:
            transcript_str = json.dumps(transcript_payload, ensure_ascii=False, separators=(",", ":"))
            transcript_label = "Transcript JSON"
        else:
            transcript_str = transcript_payload
            transcript_label = "Transcript (text)"

        prompt = (
            f"{template}\n\nRefined question: {state.target_question}{child_context}\n\n{transcript_label}:\n" + transcript_str
        )

        result = llm_adapter.call_json(prompt, temperature=0.0)
        can_answer_flag = bool(result.get("can_answer", False))
        confidence = float(result.get("confidence", 0.0))
        prefer = bool(getattr(state, 'transcript_prefer', False))
        can_answer = (can_answer_flag and (confidence >= 0.6)) or prefer
        state.transcript_can_answer = can_answer

        if can_answer:
            state.per_video_answers = {"day_transcript": transcript_str}
            state.used_transcript = True
        elif getattr(state, 'transcripts_only', False):
            fallback = "Thanks for the question Sounak, unfortunately I can't answer that yet but I'll let Joan ma'am know to help you"
            state.per_video_answers = {"fallback": fallback}
            state.transcript_can_answer = True
        
        duration_ms = int((__import__('time').time() - start_ts) * 1000)
        logger.info(
            f"transcript_answerer completed in {duration_ms}ms, can_answer={state.transcript_can_answer}"
        )
        return state

    except Exception as e:
        logger.error(f"transcript_answerer failed: {e}")
        return state
