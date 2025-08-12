import os
import json
import logging
import re

from typing import Optional, Dict, Any
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage
import vertexai
from vertexai.generative_models import GenerativeModel, Part

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
        
        # Initialize Vertex AI SDK for direct GenerativeModel usage
        try:
            vertexai.init(project=self.project_id, location=self.location)
        except Exception as e:
            logger.warning(f"vertexai.init failed or already initialized: {e}")
        
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

            # Try to sanitize common wrappers (markdown fences, leading text)
            cleaned = self._extract_json_text(response_text)
            try:
                result = json.loads(cleaned)
                logger.info("JSON response parsed successfully")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {response_text}")
                logger.error(f"Sanitized candidate: {cleaned}")
                logger.error(f"JSON parse error: {e}")
                raise ValueError(f"Invalid JSON response: {e}")
                
        except Exception as e:
            logger.error(f"JSON call failed: {e}")
            raise

    def _extract_json_text(self, text: str) -> str:
        """Extract probable JSON payload from model output.
        - Strips markdown code fences ```json ... ``` or ``` ... ```
        - If still not pure JSON, attempts to grab substring from first '{' to last '}'
        - Falls back to original stripped text
        """
        s = text.strip()
        # Remove markdown code fences
        if s.startswith("```"):
            # Remove first line fence
            s = re.sub(r"^```[a-zA-Z0-9]*\n", "", s)
            # Remove trailing fence
            s = re.sub(r"\n```\s*$", "", s)
            s = s.strip()
        # Quick path: already looks like JSON object/array
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            return s
        # Try to find the first JSON object or array in the text
        obj_match = re.search(r"\{[\s\S]*\}", s)
        arr_match = re.search(r"\[[\s\S]*\]", s)
        candidate = None
        if obj_match and arr_match:
            # Pick the longer span
            candidate = obj_match.group(0) if len(obj_match.group(0)) >= len(arr_match.group(0)) else arr_match.group(0)
        elif obj_match:
            candidate = obj_match.group(0)
        elif arr_match:
            candidate = arr_match.group(0)
        if candidate:
            return candidate.strip()
        return s
    
    def call_video(self, prompt: str, gcs_uri: str, timeout: int = 60) -> str:
        """Call Gemini 2.5 Flash with multimodal input (text + GCS video)."""
        try:
            logger.info(f"Calling video model for URI: {self._log_safe_uri(gcs_uri)}")

            # Build the video part from GCS and send together with the prompt
            video_part = Part.from_uri(gcs_uri, mime_type="video/mp4")
            model = GenerativeModel(self.model_name)

            resp = model.generate_content(
                [prompt, video_part],
                generation_config={"temperature": 0.3},
            )

            text = getattr(resp, "text", None)
            if not text and getattr(resp, "candidates", None):
                # Fallback extraction for older SDK responses
                try:
                    text = resp.candidates[0].content.parts[0].text
                except Exception:
                    text = None

            if not text or not str(text).strip():
                raise ValueError("Empty response from Gemini video analysis")

            logger.info("Video analysis completed successfully")
            return str(text).strip()

        except Exception as e:
            logger.error(f"Video call failed: {e}")
            raise

    def call_video_with_image(self, prompt: str, gcs_uri: str, image_path: str, image_mime: str | None = None, timeout: int = 60) -> str:
        """Call Gemini 2.5 Flash with multimodal input (text + local image + GCS video).
        - Reads image bytes from image_path and attaches as an image Part.
        - Attaches the video via GCS URI as before.
        """
        import mimetypes
        try:
            logger.info(f"Calling video+image model for URI: {self._log_safe_uri(gcs_uri)} with image: {image_path}")

            # Detect image mime
            if not image_mime:
                mt, _ = mimetypes.guess_type(image_path)
                image_mime = mt or "image/jpeg"

            # Read image bytes
            with open(image_path, "rb") as f:
                img_bytes = f.read()

            image_part = Part.from_data(mime_type=image_mime, data=img_bytes)
            video_part = Part.from_uri(gcs_uri, mime_type="video/mp4")
            model = GenerativeModel(self.model_name)

            resp = model.generate_content(
                [prompt, image_part, video_part],
                generation_config={"temperature": 0.3},
            )

            text = getattr(resp, "text", None)
            if not text and getattr(resp, "candidates", None):
                try:
                    text = resp.candidates[0].content.parts[0].text
                except Exception:
                    text = None

            if not text or not str(text).strip():
                raise ValueError("Empty response from Gemini video+image analysis")

            logger.info("Video+image analysis completed successfully")
            return str(text).strip()

        except Exception as e:
            logger.error(f"Video+image call failed: {e}")
            raise
    
    def _log_safe_uri(self, gcs_uri: str) -> str:
        """Log GCS URI safely (only first 20 chars)"""
        return f"{gcs_uri[:20]}..." if len(gcs_uri) > 20 else gcs_uri
