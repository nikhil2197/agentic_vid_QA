from typing import List, Dict, Optional, Sequence, Annotated
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class ConversationMessage(BaseModel):
    role: str = Field(..., description="Role of the speaker (user/assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now)

class QAState(BaseModel):
    """Shared state object passed between nodes in LangGraph"""
    
    # Core fields
    user_question: str = Field(..., description="Current question (may be child identification or original question)")
    original_question: Optional[str] = Field(None, description="Original parent question before child identification")
    child_info: Optional[str] = Field(None, description="Child's name and clothing description")
    target_videos: Optional[List[str]] = Field(None, description="Video IDs selected for deep analysis")
    target_question: Optional[str] = Field(None, description="Refined question for per-video analysis")
    per_video_answers: Optional[Dict[str, str]] = Field(None, description="Answers from each video analyzer")
    final_answer: Optional[str] = Field(None, description="Synthesized answer to user_question")
    
    # Transcript-first path
    transcript_path: Optional[str] = Field(None, description="Path to cached full-day transcript JSON")
    transcript_prompt_version: Optional[str] = Field(None, description="Version for transcript prompt to manage cache")
    transcript_can_answer: bool = Field(default=False, description="Whether transcript likely answers the refined question")
    transcript_answer: Optional[str] = Field(None, description="Answer derived from transcript if sufficient")
    used_transcript: bool = Field(default=False, description="Whether final answer came from transcript path")
    transcript_prefer: bool = Field(default=False, description="Prefer transcript path for this question (activities/skills, not child-specific)")
    
    # Conversation management - using LangGraph's standard message handling
    messages: Annotated[Sequence[BaseMessage], operator.add] = Field(default_factory=list, description="LangGraph message history")
    conversation_history: List[ConversationMessage] = Field(default_factory=list, description="Running chat history with parent")
    followup_response: Optional[str] = Field(None, description="Response to a follow-up question")
    waiting_for_child_info: bool = Field(default=False, description="Whether we're waiting for child identification")
    
    # Metadata
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True
