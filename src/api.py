"""
Minimal FastAPI backend for Agentic Video QA System
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import asyncio
from src.graph import run_main_flow
from src.state import QAState, ConversationMessage
from src.adapters.llm_adapter import LLMAdapter
from src.adapters.catalog_adapter import CatalogAdapter
from src.nodes.followup_advisor import run as followup_advisor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic Video QA API",
    description="AI-powered video question answering system for preschool videos",
    version="0.1.0"
)

# Request/Response models
class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    final_answer: str
    target_videos: List[str]
    per_video_answers: dict

class FollowupRequest(BaseModel):
    question: str
    final_answer: str
    history: List[dict]

class FollowupResponse(BaseModel):
    followup_response: str

# Global adapters (in production, use dependency injection)
_llm_adapter: Optional[LLMAdapter] = None
_catalog_adapter: Optional[CatalogAdapter] = None

@app.on_event("startup")
async def startup_event():
    """Initialize adapters on startup"""
    global _llm_adapter, _catalog_adapter
    try:
        _llm_adapter = LLMAdapter()
        _catalog_adapter = CatalogAdapter()
        logger.info("API startup completed successfully")
    except Exception as e:
        logger.error(f"API startup failed: {e}")
        raise

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Ask a question about preschool videos
    Runs the main flow: video_picker → question_refiner → video_analyzers → composer
    """
    try:
        logger.info(f"Processing question: {request.question[:50]}...")
        
        # Run main flow
        result = await run_main_flow(
            user_question=request.question,
            llm_adapter=_llm_adapter,
            catalog_adapter=_catalog_adapter
        )
        
        # Prepare response
        response = AskResponse(
            final_answer=result.final_answer,
            target_videos=result.target_videos or [],
            per_video_answers=result.per_video_answers or {}
        )
        
        logger.info(f"Question processed successfully, analyzed {len(result.target_videos or [])} videos")
        return response
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")

@app.post("/followup", response_model=FollowupResponse)
async def handle_followup(request: FollowupRequest):
    """
    Handle follow-up questions
    Runs only the followup_advisor node
    """
    try:
        logger.info(f"Processing follow-up: {request.question[:50]}...")
        
        # Convert history to ConversationMessage objects
        conversation_history = []
        for msg in request.history:
            conversation_history.append(ConversationMessage(
                role=msg.get('role', 'user'),
                content=msg.get('content', '')
            ))
        
        # Create state for followup_advisor
        followup_state = QAState(
            user_question=request.question,  # This should be the original question
            final_answer=request.final_answer,
            conversation_history=conversation_history
        )
        
        # Run followup_advisor
        result = await followup_advisor(followup_state, _llm_adapter)
        
        response = FollowupResponse(
            followup_response=result.followup_response
        )
        
        logger.info("Follow-up processed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error processing follow-up: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process follow-up: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "agentic-video-qa"}

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "service": "Agentic Video QA API",
        "version": "0.1.0",
        "endpoints": {
            "POST /ask": "Ask a question about preschool videos",
            "POST /followup": "Handle follow-up questions",
            "GET /health": "Health check"
        }
    }
