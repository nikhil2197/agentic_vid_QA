import logging
from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

async def run(state: QAState, llm_adapter: LLMAdapter) -> QAState:
    """
    Node: child_identifier
    Input: user_question (original question)
    Output: child_info (name and clothing description)
    """
    start_time = __import__('time').time()
    
    try:
        # If child info has already been provided, restore and proceed
        if getattr(state, 'child_info', None):
            state.waiting_for_child_info = False
            if state.original_question:
                state.user_question = state.original_question
            duration_ms = int((__import__('time').time() - start_time) * 1000)
            logger.info(f"child_identifier completed in {duration_ms}ms, child info available, proceeding with original question")
        else:
            # Determine if child identification is needed via LLM classification
            requires_child = True
            try:
                # Load classification prompt template
                with open("prompts/child_identifier_classify.txt", "r") as f:
                    classify_template = f.read()
                classification_prompt = classify_template.format(question=state.user_question)
                classification = llm_adapter.call_json(classification_prompt)
                requires_child = bool(classification.get("requires_child", True))
            except Exception as cls_e:
                logger.warning(f"child_identifier classification failed: {cls_e}, defaulting to requiring child info")
                requires_child = True

            if requires_child:
                # Prompt user for child identification using template
                with open("prompts/child_identifier.txt", "r") as f:
                    child_question = f.read().strip()
                state.original_question = state.user_question
                state.user_question = child_question
                from src.state import ConversationMessage
                if not getattr(state, 'conversation_history', None):
                    state.conversation_history = []
                state.conversation_history.append(ConversationMessage(role="assistant", content=child_question))
                state.waiting_for_child_info = True
                duration_ms = int((__import__('time').time() - start_time) * 1000)
                logger.info(f"child_identifier completed in {duration_ms}ms, requesting child identification")
            else:
                # No child identification needed, proceed
                state.waiting_for_child_info = False
                duration_ms = int((__import__('time').time() - start_time) * 1000)
                logger.info(f"child_identifier completed in {duration_ms}ms, child identification not required, proceeding")
    except Exception as e:
        logger.error(f"child_identifier failed: {e}")
        # Fallback: proceed without child identification
        state.waiting_for_child_info = False
    
    # Return the modified state to preserve all fields
    return state
