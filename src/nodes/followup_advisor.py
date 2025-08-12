import logging
from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

def run(state: QAState, llm_adapter: LLMAdapter) -> QAState:
    """
    Node: followup_advisor
    Input: user_question, final_answer, conversation_history
    Output: followup_response (conversational response with actionable advice)
    """
    start_time = __import__('time').time()
    
    try:
        # Load prompt
        with open("prompts/followup_advisor.txt", "r") as f:
            prompt_template = f.read()
        
        # Format conversation history
        history_str = ""
        if state.conversation_history:
            history_lines = []
            for msg in state.conversation_history:
                history_lines.append(f"{msg.role}: {msg.content}")
            history_str = "\n".join(history_lines)
        
        # Build prompt
        prompt = f"{prompt_template}\n\nOriginal question: {state.user_question}\n\nFinal answer: {state.final_answer}\n\nConversation history:\n{history_str}"
        
        # Call LLM for text response
        response = llm_adapter.call_text(prompt, temperature=0.7)
        
        # Clean and validate response
        if response and len(response.strip()) > 0:
            # Rely on prompt to enforce length/format; no hard truncation here
            state.followup_response = response.strip()
        else:
            # Fallback: request more information
            logger.warning("Empty response from followup_advisor, using fallback")
            state.followup_response = "I'd be happy to help further! Could you please provide more specific details about what you'd like to know or what actions you'd like guidance on?"
        
        # Log success
        duration_ms = int((__import__('time').time() - start_time) * 1000)
        logger.info(f"followup_advisor completed in {duration_ms}ms, output_fields_set: ['followup_response']")
        
    except Exception as e:
        logger.error(f"followup_advisor failed: {e}")
        # Fallback: basic response
        state.followup_response = "I'm here to help! Please let me know if you have any other questions about your child's day."
    
    # Return the modified state to preserve all fields
    return state
