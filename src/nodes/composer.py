import logging
from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

def run(state: QAState, llm_adapter: LLMAdapter) -> QAState:
    """
    Node: composer
    Input: user_question, per_video_answers
    Output: final_answer (synthesized answer)
    """
    start_time = __import__('time').time()
    
    try:
        # Load prompt
        with open("prompts/composer.txt", "r") as f:
            prompt_template = f.read()
        
        # Build prompt with video answers
        video_answers_str = "\n".join([f"Video {vid}: {answer}" for vid, answer in state.per_video_answers.items()])
        
        prompt = f"{prompt_template}\n\nOriginal question: {state.user_question}\n\nVideo answers:\n{video_answers_str}"
        
        # Call LLM for text response
        response = llm_adapter.call_text(prompt, temperature=0.7)
        
        # Clean and validate response
        if response and len(response.strip()) > 0:
            # Ensure it's one paragraph (under 140 words as per guardrails)
            words = response.strip().split()
            if len(words) > 140:
                # Truncate to first 140 words
                response = " ".join(words[:140]) + "..."
            
            state.final_answer = response.strip()
        else:
            # Fallback: concatenate video answers
            logger.warning("Empty response from composer, using fallback")
            fallback_parts = []
            for vid, answer in state.per_video_answers.items():
                if answer and answer != "Not enough evidence in this video.":
                    fallback_parts.append(f"From video {vid}: {answer}")
            
            if fallback_parts:
                state.final_answer = " ".join(fallback_parts)
            else:
                state.final_answer = "I couldn't find enough evidence in the available videos to answer your question."
        
        # Log success
        duration_ms = int((__import__('time').time() - start_time) * 1000)
        logger.info(f"composer completed in {duration_ms}ms, output_fields_set: ['final_answer']")
        
    except Exception as e:
        logger.error(f"composer failed: {e}")
        # Fallback: basic message
        state.final_answer = "I encountered an issue while analyzing the videos. Please try rephrasing your question."
    
    # Return the modified state to preserve all fields
    return state
