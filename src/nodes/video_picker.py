import logging
from typing import List
from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter
from src.adapters.catalog_adapter import CatalogAdapter

logger = logging.getLogger(__name__)

def run(state: QAState, llm_adapter: LLMAdapter, catalog_adapter: CatalogAdapter) -> QAState:
    """
    Node: video_picker
    Input: user_question
    Output: target_videos (list of video IDs)
    """
    start_time = __import__('time').time()
    
    try:
        # Load prompt
        with open("prompts/video_picker.txt", "r") as f:
            prompt_template = f.read()
        
        # Get catalog info for prompt with enhanced context
        catalog = catalog_adapter.list_catalog()
        catalog_info = []
        for video in catalog:
            # Calculate duration if start and end times are available
            duration = "Unknown"
            start_time = video.get('start-time')
            end_time = video.get('end-time')
            
            # Handle both numeric and time string formats
            if start_time is not None and end_time is not None:
                try:
                    if isinstance(start_time, (int, float)) and isinstance(end_time, (int, float)):
                        # Numeric times (minutes)
                        duration = f"{end_time - start_time} minutes"
                    elif isinstance(start_time, str) and isinstance(end_time, str):
                        # Time strings like "10:00"
                        try:
                            # Parse time strings and calculate duration
                            start_parts = start_time.split(':')
                            end_parts = end_time.split(':')
                            if len(start_parts) == 2 and len(end_parts) == 2:
                                start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
                                end_minutes = int(end_parts[0]) * 60 + int(start_parts[1])
                                duration = f"{end_minutes - start_minutes} minutes"
                        except:
                            duration = f"{start_time} - {end_time}"
                    else:
                        duration = f"{start_time} - {end_time}"
                except:
                    duration = f"{start_time} - {end_time}"
            
            catalog_info.append({
                'id': video['id'],
                'session-type': video.get('session-type', 'Unknown'),
                'start-time': video.get('start-time', 'Unknown'),
                'end-time': video.get('end-time', 'Unknown'),
                'duration': duration,
                'act-description': video.get('act-description', 'No description provided'),
                'gcs_uri': video.get('gcs_uri', 'No URI')[:50] + '...' if video.get('gcs_uri') else 'No URI'
            })
        
        # Build prompt with child information if available
        child_context = ""
        if hasattr(state, 'child_info') and state.child_info:
            child_context = f"\n\nChild Information: {state.child_info}"
        
        # Use original question if available, otherwise use current question
        question_to_use = getattr(state, 'original_question', state.user_question)
        
        prompt = f"{prompt_template}\n\nQuestion: {question_to_use}{child_context}\n\nCatalog: {catalog_info}"
        
        # Call LLM for JSON response
        response = llm_adapter.call_json(prompt, temperature=0.0)
        
        # Extract video IDs
        if 'videos' in response and isinstance(response['videos'], list):
            video_ids = response['videos']
            # Filter to only existing video IDs and limit to 5
            valid_ids = [vid for vid in video_ids if catalog_adapter.has(vid)][:5]
            
            if not valid_ids:
                # Fallback: use first 3 videos
                logger.warning("No valid video IDs returned, using fallback")
                valid_ids = list(catalog.keys())[:3]
            
            state.target_videos = valid_ids
            
        else:
            # Fallback: use first 3 videos
            logger.warning("Invalid JSON response, using fallback")
            state.target_videos = list(catalog.keys())[:3]
        
        # Log success
        duration_ms = int((__import__('time').time() - start_time) * 1000)
        logger.info(f"video_picker completed in {duration_ms}ms, output_fields_set: ['target_videos'], target_videos: {state.target_videos}")
        
    except Exception as e:
        logger.error(f"video_picker failed: {e}")
        # Fallback: use first 3 videos
        catalog = catalog_adapter.list_catalog()
        state.target_videos = [video['id'] for video in catalog[:3]]
    
    # Return the modified state to preserve all fields
    return state
