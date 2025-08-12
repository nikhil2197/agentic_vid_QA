import logging
from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

def run(state: QAState, llm_adapter: LLMAdapter) -> QAState:
    """
    Node: transcript_router
    Input: target_question
    Output: transcript_prefer (bool)
    """
    start_ts = __import__('time').time()
    try:
        with open("prompts/transcript_router.txt", "r") as f:
            template = f.read()

        question = getattr(state, 'target_question', None) or state.user_question
        prompt = f"{template}\n\nRefined question: {question}"
        result = llm_adapter.call_json(prompt, temperature=0.0)
        prefer = bool(result.get("prefer_transcript", False))
        state.transcript_prefer = prefer

        dur = int((__import__('time').time() - start_ts) * 1000)
        logger.info(f"transcript_router completed in {dur}ms, prefer_transcript={prefer}")
        return state
    except Exception as e:
        logger.error(f"transcript_router failed: {e}")
        state.transcript_prefer = False
        return state

