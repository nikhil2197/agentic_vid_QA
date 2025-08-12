from src.state import QAState

def run(state: QAState) -> QAState:
    """
    Node: followup_reentry
    Purpose: Prepare state to re-enter the main pipeline with the follow-up question.
    - Sets user_question to followup_next_question
    - Clears waiting_for_child_info (demo may pre-fill child elsewhere)
    """
    try:
        fq = (getattr(state, 'followup_next_question', None) or '').strip()
        if fq:
            state.user_question = fq
        state.waiting_for_child_info = False
        # Clear route after consuming
        state.followup_route = None
    except Exception:
        pass
    return state

