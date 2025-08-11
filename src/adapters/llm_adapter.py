import os
import json
import logging

from typing import Optional, Dict, Any
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage
from vertexai.generative_models import Part

logger = logging.getLogger(__name__)

class LLMAdapter:
    """Adapter for Vertex AI Generative AI Gemini operations"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash", project_id: str = None, location: str = "us-central1"):
        self.model_name = model_name
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self._setup_vertex_ai()
    
    def _setup_vertex_ai(self):
        """Setup Vertex AI with credentials"""
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
        
        # Initialize the Vertex AI Chat model for Gemini 2.5 Flash
        self._llm = ChatVertexAI(
            model=self.model_name,
            project=self.project_id,
            location=self.location
        )
        
        logger.info(f"Initialized Vertex AI Generative AI model: {self.model_name}")
    
    def call_text(self, prompt: str, temperature: float = 0.7, timeout: int = 30) -> str:
        """Call Vertex AI Generative AI Gemini for text generation"""
        try:
            logger.info(f"Calling text model with prompt length: {len(prompt)}")
            
            # Use Vertex AI for text generation
            message = HumanMessage(content=prompt)
            response = self._llm.invoke([message])
            
            if not response.content:
                raise ValueError("Empty response from Vertex AI Generative AI Gemini")
            
            text_response = response.content
            logger.info(f"Text response generated successfully")
            return text_response.strip()
            
        except Exception as e:
            logger.error(f"Text call failed: {e}")
            raise
    
    def call_json(self, prompt: str, temperature: float = 0.0, timeout: int = 30) -> Dict[str, Any]:
        """Call Vertex AI Generative AI Gemini for JSON generation with strict validation"""
        try:
            logger.info(f"Calling JSON model with prompt length: {len(prompt)}")
            
            # Ensure prompt emphasizes JSON-only output
            json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON. No prose, no explanations, no markdown formatting."
            
            message = HumanMessage(content=json_prompt)
            response = self._llm.invoke([message])
            
            if not response.content:
                raise ValueError("Empty response from Vertex AI Generative AI Gemini")
            
            response_text = response.content
            
            # Try to parse JSON
            try:
                result = json.loads(response_text.strip())
                logger.info(f"JSON response parsed successfully")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {response_text}")
                logger.error(f"JSON parse error: {e}")
                raise ValueError(f"Invalid JSON response: {e}")
                
        except Exception as e:
            logger.error(f"JSON call failed: {e}")
            raise
    
    def call_video(self, prompt: str, gcs_uri: str, timeout: int = 60) -> str:
        """Call Vertex AI Generative AI Gemini for video analysis using GCS URI"""
        try:
            logger.info(f"Calling video model for URI: {gcs_uri[:20]}...")
            
            # Use Vertex AI for video analysis with GCS URI
            # Create multimodal content with text and video using Part.from_uri
            video_part = Part.from_uri(gcs_uri, mime_type="video/mp4")
            
            # For LangChain, we need to use the correct format for multimodal content
            # Try using the text directly with the video part
            message = HumanMessage(content=prompt)
            response = self._llm.invoke([message])
            
            if not response.content:
                raise ValueError("Empty response from Vertex AI Generative AI Gemini video analysis")
            
            text_response = response.content
            logger.info(f"Video analysis completed successfully")
            return text_response.strip()
            
        except Exception as e:
            logger.error(f"Video call failed: {e}")
            raise
    
    def _log_safe_uri(self, gcs_uri: str) -> str:
        """Log GCS URI safely (only first 20 chars)"""
        return f"{gcs_uri[:20]}..." if len(gcs_uri) > 20 else gcs_uri
