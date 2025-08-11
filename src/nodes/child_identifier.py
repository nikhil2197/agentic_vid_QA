import logging
from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

def run(state: QAState, llm_adapter: LLMAdapter) -> QAState:
    """
    Node: child_identifier
    Input: user_question (original question)
    Output: child_info (name and clothing description)
    """
    start_time = __import__('time').time()
    
    try:
        # Check if this is the first interaction (no child_info yet)
        if not hasattr(state, 'child_info') or not state.child_info:
            # This is the initial question - ask for child identification
            child_question = "Can you tell me your child's name and describe what they were wearing today?"
            
            # Store the original question for later
            state.original_question = state.user_question
            
            # Set the current question to the child identification prompt
            state.user_question = child_question
            
            # Add to conversation history
            from src.state import ConversationMessage
            if not hasattr(state, 'conversation_history'):
                state.conversation_history = []
            state.conversation_history.append(ConversationMessage(role="assistant", content=child_question))
            
            # Set a flag to indicate we're waiting for child info
            state.waiting_for_child_info = True
            
            # Log the child identification request
            duration_ms = int((__import__('time').time() - start_time) * 1000)
            logger.info(f"child_identifier completed in {duration_ms}ms, output_fields_set: ['user_question', 'waiting_for_child_info'], requesting child identification")
            
        else:
            # Child info already provided, proceed with original question
            state.waiting_for_child_info = False
            
            # Log that we're proceeding with the original question
            duration_ms = int((__import__('time').time() - start_time) * 1000)
            logger.info(f"child_identifier completed in {duration_ms}ms, child info already available, proceeding with original question")
        
    except Exception as e:
        logger.error(f"child_identifier failed: {e}")
        # Fallback: proceed without child identification
        state.waiting_for_child_info = False
    
    # Return the modified state to preserve all fields
    return state
