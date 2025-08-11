import logging
from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

def run(state: QAState, llm_adapter: LLMAdapter) -> QAState:
    """
    Node: question_refiner
    Input: user_question
    Output: target_question (refined question for per-video analysis)
    """
    start_time = __import__('time').time()
    
    try:
        # Load prompt
        with open("prompts/question_refiner.txt", "r") as f:
            prompt_template = f.read()
        
        # Build prompt with child information if available
        child_context = ""
        if hasattr(state, 'child_info') and state.child_info:
            child_context = f"\n\nChild Information: {state.child_info}"
        
        # Use original question if available, otherwise use current question
        question_to_use = getattr(state, 'original_question', state.user_question)
        
        prompt = f"{prompt_template}\n\nOriginal question: {question_to_use}{child_context}"
        
        # Call LLM for text response
        response = llm_adapter.call_text(prompt, temperature=0.7)
        
        # Clean and validate response
        if response and len(response.strip()) > 0:
            # Ensure it's one sentence
            sentences = response.strip().split('.')
            if len(sentences) > 1:
                # Take first sentence if multiple
                refined_question = sentences[0].strip() + '.'
            else:
                refined_question = response.strip()
            
            state.target_question = refined_question
        else:
            # Fallback to original question
            logger.warning("Empty response from question_refiner, using original question")
            state.target_question = state.user_question
        
        # Log success
        duration_ms = int((__import__('time').time() - start_time) * 1000)
        logger.info(f"question_refiner completed in {duration_ms}ms, output_fields_set: ['target_question']")
        
    except Exception as e:
        logger.error(f"question_refiner failed: {e}")
        # Fallback to original question
        state.target_question = state.user_question
    
    # Return the modified state to preserve all fields
    return state
