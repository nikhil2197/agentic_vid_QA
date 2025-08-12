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
        state.transcript_answer = (result.get("answer", "") or "").strip()

        if can_answer and state.transcript_answer:
            # Feed through composer path by setting per_video_answers to use transcript
            state.per_video_answers = {"transcript": state.transcript_answer}
        
        duration_ms = int((__import__('time').time() - start_ts) * 1000)
        logger.info(
            f"transcript_answerer completed in {duration_ms}ms, can_answer={state.transcript_can_answer}"
        )
        return state

    except Exception as e:
        logger.error(f"transcript_answerer failed: {e}")
        return state
