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
        
        # Classify the latest follow-up to decide routing
        latest_followup = None
        if state.conversation_history:
            # pick the last user message content
            for msg in reversed(state.conversation_history):
                if getattr(msg, 'role', '') == 'user' and getattr(msg, 'content', ''):
                    latest_followup = msg.content.strip()
                    break
        if latest_followup:
            try:
                with open("prompts/followup_router.txt", "r") as f:
                    router_template = f.read()
                router_prompt = f"{router_template}\n\nLatest follow-up question: {latest_followup}"
                route_obj = llm_adapter.call_json(router_prompt, temperature=0.0)
                route = str(route_obj.get('route', 'parenting_help'))
                state.followup_route = route
                if route in ("transcript_child", "transcript_day"):
                    state.followup_next_question = latest_followup
            except Exception as re:
                logger.warning(f"followup routing failed: {re}")
                state.followup_route = None

        # Log success
        duration_ms = int((__import__('time').time() - start_time) * 1000)
        logger.info(f"followup_advisor completed in {duration_ms}ms, output_fields_set: ['followup_response','followup_route']")
        
    except Exception as e:
        logger.error(f"followup_advisor failed: {e}")
        # Fallback: basic response
        state.followup_response = "I'm here to help! Please let me know if you have any other questions about your child's day."
    
    # Return the modified state to preserve all fields
    return state
