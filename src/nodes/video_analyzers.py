import logging
import asyncio
from typing import Dict
from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter
from src.adapters.catalog_adapter import CatalogAdapter

logger = logging.getLogger(__name__)

def _analyze_single_video(
    video_id: str, 
    target_question: str, 
    state: QAState,
    llm_adapter: LLMAdapter, 
    catalog_adapter: CatalogAdapter
) -> tuple[str, str]:
    """Analyze a single video and return (video_id, answer)"""
    try:
        # Get video URI
        gcs_uri = catalog_adapter.get_uri(video_id)
        
        # Load prompt
        with open("prompts/video_analyzer.txt", "r") as f:
            prompt_template = f.read()
        
        # Build prompt with child information if available
        child_context = ""
        if hasattr(state, 'child_info') and state.child_info:
            child_context = f"\n\nChild Information: {state.child_info}"
        
        prompt = f"{prompt_template}\n\nQuestion: {target_question}{child_context}"
        
        # Call LLM for video analysis (multimodal with GCS URI)
        answer = llm_adapter.call_video(prompt=prompt, gcs_uri=gcs_uri)
        
        return video_id, answer
        
    except Exception as e:
        logger.error(f"Video analysis failed for {video_id}: {e}")
        return video_id, "Not enough evidence in this video."

def run(state: QAState, llm_adapter: LLMAdapter, catalog_adapter: CatalogAdapter) -> QAState:
    """
    Node: video_analyzers
    Input: target_question, target_videos
    Output: per_video_answers (dict: video_id -> answer)
    """
    start_time = __import__('time').time()
    
    try:
        if not state.target_videos:
            logger.warning("No target videos to analyze")
            state.per_video_answers = {}
            return state
        
        # Run video analyses sequentially since we're now synchronous
        results = []
        for video_id in state.target_videos:
            try:
                result = _analyze_single_video(video_id, state.target_question, state, llm_adapter, catalog_adapter)
                results.append(result)
            except Exception as e:
                logger.error(f"Video analysis failed for {video_id}: {e}")
                results.append((video_id, f"Error analyzing video: {e}"))
        
        # Process results
        per_video_answers = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Video analysis task failed: {result}")
                continue
            
            video_id, answer = result
            per_video_answers[video_id] = answer
        
        state.per_video_answers = per_video_answers
        
        # Log success
        duration_ms = int((__import__('time').time() - start_time) * 1000)
        video_ids = list(per_video_answers.keys())
        logger.info(f"video_analyzers completed in {duration_ms}ms, output_fields_set: ['per_video_answers'], video_ids: {video_ids}")
        
    except Exception as e:
        logger.error(f"video_analyzers failed: {e}")
        # Fallback: empty answers
        state.per_video_answers = {}
    
    # Return the modified state to preserve all fields
    return state
