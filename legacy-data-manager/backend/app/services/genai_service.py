from typing import Dict, List, Optional
from huggingface_hub import InferenceClient
from ..core.config import settings
import logging
import json
import asyncio
from .google_drive import GoogleDriveService
import time

logger = logging.getLogger(__name__)

class GenAIService:
    def __init__(self):
        self.client = InferenceClient(token=settings.HUGGINGFACE_API_TOKEN)
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"  # Using Mixtral 8x7B
        self.drive_service = GoogleDriveService()
        self.rate_limit = 10  # requests per minute
        self.last_request_time = 0

    async def _extract_text_content(self, file_id: str, mime_type: str) -> str:
        """Extract text content from a file based on its mime type."""
        try:
            content = await self.drive_service.get_file_content(file_id)
            
            # Handle different mime types
            if mime_type == 'application/pdf':
                # TODO: Implement PDF text extraction
                return content[:50000]  # Limit content size
            elif mime_type.startswith('text/'):
                return content[:50000]  # Limit content size
            elif mime_type.startswith('application/vnd.google-apps.'):
                # Handle Google Workspace files
                return content[:50000]
            else:
                logger.warning(f"Unsupported mime type: {mime_type}")
                return ""
        except Exception as e:
            logger.error(f"Error extracting text content: {str(e)}")
            return ""

    async def _rate_limit_wait(self):
        """Implement rate limiting."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < (60 / self.rate_limit):
            await asyncio.sleep((60 / self.rate_limit) - time_since_last_request)
        self.last_request_time = time.time()

    async def analyze_document(self, content: str, filename: str) -> Dict:
        """Analyze document content and suggest categories."""
        try:
            await self._rate_limit_wait()
            
            # Prepare the prompt for the AI
            prompt = f"""<s>[INST] You are a document categorization expert. Analyze the following document content and suggest appropriate categories.
            Document name: {filename}
            
            Content:
            {content[:8000]}  # Increased content length due to Mixtral's larger context window
            
            Please suggest categories from the following hierarchy:
            - Financial Documents
              - Invoices
              - Receipts
              - Tax Documents
            - Legal Documents
              - Contracts
              - Agreements
              - Certificates
            - HR Documents
              - Employee Records
              - Policies
              - Reports
            - Technical Documents
              - Specifications
              - Manuals
              - Documentation
            
            Provide your response in the following JSON format:
            {{
                "primary_category": "string",
                "secondary_category": "string",
                "confidence_score": float,
                "explanation": "string",
                "key_topics": ["string"]
            }}
            
            Ensure the response is valid JSON and follows the exact format specified. [/INST]"""

            # Call Hugging Face API
            response = self.client.text_generation(
                prompt,
                model=self.model,
                max_new_tokens=800,
                temperature=0.2,
                top_p=0.9,
                repetition_penalty=1.1,
                return_full_text=False
            )

            # Parse the response
            response_text = response
            # Find the JSON part in the response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Validate the response format
                required_fields = ["primary_category", "secondary_category", "confidence_score", "explanation", "key_topics"]
                if not all(field in result for field in required_fields):
                    raise ValueError("Response missing required fields")
                
                # Ensure confidence_score is a float
                if not isinstance(result["confidence_score"], (int, float)):
                    raise ValueError("confidence_score must be a number")
                
                return result
            else:
                raise ValueError("Could not find valid JSON in response")

        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            raise

    async def analyze_directory(self, files: List[Dict]) -> List[Dict]:
        """Analyze multiple files in a directory."""
        results = []
        for file in files:
            try:
                # Extract text content based on file type
                content = await self._extract_text_content(file['id'], file['mimeType'])
                if not content:
                    logger.warning(f"Could not extract content from file: {file['name']}")
                    continue

                # Analyze the document
                analysis = await self.analyze_document(content, file['name'])
                
                # Combine file metadata with analysis
                result = {
                    "file_id": file['id'],
                    "name": file['name'],
                    "mime_type": file['mimeType'],
                    "analysis": analysis
                }
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing file {file['name']}: {str(e)}")
                continue
        
        return results 