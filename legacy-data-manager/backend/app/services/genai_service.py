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
            {content[:8000]}
            
            Based on the content, categorize this document and provide the following information in a structured format:
            1. Primary category (choose one): Financial Documents, Legal Documents, HR Documents, or Technical Documents
            2. Secondary category based on the primary category selected
            3. Confidence score between 0 and 1
            4. Brief explanation of your categorization
            5. Key topics found in the document

            Format your response as follows (do not include any other text):
            {{
                "primary_category": "one of the main categories",
                "secondary_category": "appropriate subcategory",
                "confidence_score": 0.95,
                "explanation": "brief explanation",
                "key_topics": ["topic1", "topic2"]
            }}[/INST]</s>"""

            # Call Hugging Face API
            response = self.client.text_generation(
                prompt,
                model=self.model,
                max_new_tokens=800,
                temperature=0.1,  # Reduced temperature for more consistent output
                top_p=0.9,
                repetition_penalty=1.1,
                return_full_text=False
            )

            # Clean and parse the response
            response_text = response.strip()
            
            # Find the JSON part in the response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx == -1 or end_idx <= start_idx:
                logger.warning(f"Could not find valid JSON structure in response: {response_text}")
                return {
                    "primary_category": "Unknown",
                    "secondary_category": "Unknown",
                    "confidence_score": 0.0,
                    "explanation": "Could not analyze document",
                    "key_topics": []
                }
            
            try:
                # Extract and clean the JSON string
                json_str = response_text[start_idx:end_idx]
                # Replace any escaped characters that might cause issues
                json_str = json_str.replace('\\"', '"').replace('\\n', ' ').replace('\\', '')
                result = json.loads(json_str)
                
                # Validate and sanitize the response
                result = {
                    "primary_category": str(result.get("primary_category", "Unknown")),
                    "secondary_category": str(result.get("secondary_category", "Unknown")),
                    "confidence_score": float(result.get("confidence_score", 0.0)),
                    "explanation": str(result.get("explanation", "No explanation provided")),
                    "key_topics": [str(topic) for topic in result.get("key_topics", [])]
                }
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}\nResponse text: {response_text}")
                return {
                    "primary_category": "Unknown",
                    "secondary_category": "Unknown",
                    "confidence_score": 0.0,
                    "explanation": f"Error parsing analysis results: {str(e)}",
                    "key_topics": []
                }

        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            return {
                "primary_category": "Unknown",
                "secondary_category": "Unknown",
                "confidence_score": 0.0,
                "explanation": f"Error during analysis: {str(e)}",
                "key_topics": []
            }

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