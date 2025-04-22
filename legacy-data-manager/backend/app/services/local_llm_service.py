from llama_cpp import Llama
import pytesseract
from PIL import Image
import io
import logging
from typing import Dict, List, Optional
import os

logger = logging.getLogger(__name__)

class LocalLLMService:
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "llama-2-7b-chat.gguf")
        self._is_ready = False
        self._init_model()

        # Configure Tesseract
        self.tesseract_cmd = '/opt/homebrew/bin/tesseract'  # Update this path based on your system
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def _init_model(self):
        """Initialize the LLM model."""
        try:
            logger.info(f"Attempting to initialize LLM model from path: {self.model_path}")
            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found at {self.model_path}")
                return
            
            logger.info("Model file found, initializing Llama...")
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=2048,  # Context window
                n_threads=4   # Number of CPU threads to use
            )
            self._is_ready = True
            logger.info("LLM model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM model: {str(e)}")
            logger.exception("Detailed error:")
            self._is_ready = False

    def is_ready(self) -> bool:
        """Check if the LLM service is ready to process requests."""
        ready = self._is_ready and self.model is not None
        logger.info(f"LLM service ready status: {ready}")
        return ready

    async def process_image(self, image_data: bytes) -> str:
        """Extract text from image using Tesseract OCR."""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"Error processing image with OCR: {e}")
            return ""

    async def analyze_content(self, content: str) -> Dict:
        """Analyze text content using local Llama model."""
        if not self.model:
            logger.error("Llama model not initialized")
            return {}

        try:
            # Prompt engineering for PII detection
            prompt = f"""Analyze the following text for any sensitive or personal information. 
            Look for:
            1. Personal Identifiable Information (PII)
            2. Financial information
            3. Legal information
            4. Confidential business information
            5. Healthcare information

            Text to analyze:
            {content}

            Provide a JSON response with these fields:
            - has_sensitive_info: boolean
            - confidence: float (0-1)
            - categories: list of found sensitive information types
            - explanation: brief explanation of findings
            """

            # Get response from model
            response = self.model(
                prompt,
                max_tokens=500,
                temperature=0,
                stop=["```"],
                echo=False
            )

            # Parse response and return structured data
            # Note: You might need to improve response parsing based on actual model output
            return {
                "has_sensitive_info": True if "yes" in response["choices"][0]["text"].lower() else False,
                "confidence": 0.9,  # You'll need to extract this from the response
                "categories": [],  # Parse categories from response
                "explanation": response["choices"][0]["text"]
            }

        except Exception as e:
            logger.error(f"Error analyzing content with Llama: {e}")
            return {
                "has_sensitive_info": False,
                "confidence": 0,
                "categories": [],
                "explanation": f"Error during analysis: {str(e)}"
            }

    async def scan_file(self, file_content: bytes, mime_type: str) -> Dict:
        """Scan a file for sensitive information."""
        try:
            # Extract text based on file type
            text_content = ""
            if mime_type.startswith('image/'):
                text_content = await self.process_image(file_content)
            else:
                # For text-based files, assume content is already text
                text_content = file_content.decode('utf-8') if isinstance(file_content, bytes) else file_content

            # Analyze the extracted text
            if text_content:
                return await self.analyze_content(text_content)
            else:
                return {
                    "has_sensitive_info": False,
                    "confidence": 0,
                    "categories": [],
                    "explanation": "No text content could be extracted"
                }

        except Exception as e:
            logger.error(f"Error scanning file: {e}")
            return {
                "has_sensitive_info": False,
                "confidence": 0,
                "categories": [],
                "explanation": f"Error during scanning: {str(e)}"
            } 