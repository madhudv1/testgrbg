from fastapi import APIRouter, HTTPException, Request, Depends, status
from typing import Dict, List, Optional
from ....services.google_drive import GoogleDriveService
from ....core.config import settings
import logging
from ....services.genai_service import GenAIService
from datetime import datetime, timezone, timedelta
from ....services.local_llm_service import LocalLLMService
from ....services.rate_limiter import LLMRateLimiter
from fastapi.responses import RedirectResponse
import json
import uuid
import asyncio
from ....core.auth import get_current_user

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
drive_service = GoogleDriveService()
genai_service = GenAIService()

# Initialize services
local_llm = LocalLLMService()
rate_limiter = LLMRateLimiter()

def categorize_file_by_age(file: Dict) -> str:
    """
    Categorize a file based on its modification date.
    Returns one of: "moreThanThreeYears", "oneToThreeYears", "lessThanOneYear"
    """
    try:
        modified_time = datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        age = now - modified_time
        
        if age > timedelta(days=3*365):  # More than 3 years
            return "moreThanThreeYears"
        elif age > timedelta(days=365):   # Between 1-3 years
            return "oneToThreeYears"
        else:                             # Less than 1 year
            return "lessThanOneYear"
    except Exception as e:
        logger.error(f"Error categorizing file age: {e}")
        return "moreThanThreeYears"  # Default to oldest category if we can't determine age

@router.get("/auth/url")
async def get_auth_url_redirect():
    """Redirect to the new auth URL endpoint."""
    logger.info("Redirecting old auth URL endpoint to new endpoint")
    return RedirectResponse(url="/api/v1/auth/google/login")

@router.get("/auth/callback")
async def auth_callback_redirect(code: str):
    """Redirect to the new auth callback endpoint."""
    logger.info("Redirecting old auth callback endpoint to new endpoint")
    return RedirectResponse(url=f"/api/v1/auth/google/callback?code={code}")

@router.get("/auth/status")
async def get_auth_status_redirect():
    """Redirect to the new auth status endpoint."""
    logger.info("Redirecting old auth status endpoint to new endpoint")
    return RedirectResponse(url="/api/v1/auth/google/status")

@router.get("/files")
async def list_files(page_size: int = 100):
    """List files from Google Drive."""
    if not drive_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please authenticate first.")
    try:
        files = drive_service.list_files(page_size)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/inactive")
async def list_inactive_files():
    """List inactive files from Google Drive."""
    if not drive_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please authenticate first.")
    try:
        files = drive_service.get_inactive_files()
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listing inactive files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/{file_id}")
async def get_file_metadata(file_id: str):
    """Get metadata for a specific file."""
    if not drive_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please authenticate first.")
    try:
        metadata = drive_service.get_file_metadata(file_id)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/directories/{folder_id}/files")
async def list_directory_files(folder_id: str, page_size: int = 100):
    """List files in a specific directory."""
    if not drive_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please authenticate first.")
    try:
        files = drive_service.list_directory(folder_id, page_size)
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listing directory files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/directories/{folder_id}/analyze")
async def analyze_directory(
    folder_id: str,
    recursive: bool = True,
    drive_service: GoogleDriveService = Depends(get_current_user)
):
    """
    Analyze a directory and its contents, optionally including subdirectories if recursive=True.
    Returns statistics about file types and sensitive content organized by age categories.
    """
    try:
        # Initialize the local LLM service
        local_llm = LocalLLMService()
        
        # Get all files in the directory
        files = await drive_service.list_directory(folder_id, recursive=recursive)
        
        # Initialize response structure
        response = {
            "moreThanThreeYears": {
                "total_documents": 0,
                "total_sensitive": 0,
                "file_types": {
                    "documents": [],
                    "spreadsheets": [],
                    "presentations": [],
                    "pdfs": [],
                    "images": [],
                    "others": []
                },
                "sensitive_info": {
                    "email": [],
                    "ssn": [],
                    "phone": [],
                    "credit_card": [],
                    "ip_address": []
                }
            },
            "oneToThreeYears": {
                "total_documents": 0,
                "total_sensitive": 0,
                "file_types": {
                    "documents": [],
                    "spreadsheets": [],
                    "presentations": [],
                    "pdfs": [],
                    "images": [],
                    "others": []
                },
                "sensitive_info": {
                    "email": [],
                    "ssn": [],
                    "phone": [],
                    "credit_card": [],
                    "ip_address": []
                }
            },
            "lessThanOneYear": {
                "total_documents": 0,
                "total_sensitive": 0,
                "file_types": {
                    "documents": [],
                    "spreadsheets": [],
                    "presentations": [],
                    "pdfs": [],
                    "images": [],
                    "others": []
                },
                "sensitive_info": {
                    "email": [],
                    "ssn": [],
                    "phone": [],
                    "credit_card": [],
                    "ip_address": []
                }
            },
            "scan_complete": False
        }
        
        # Process each file
        for file in files:
            # Categorize by age
            age_category = categorize_file_by_age(file)
            
            # Increment total documents for this age category
            response[age_category]["total_documents"] += 1
            
            # Categorize file type and add to appropriate list
            file_type = categorize_file_type(file)
            response[age_category]["file_types"][file_type].append(file)
            
            try:
                # Get file content and analyze with LLM
                content = await drive_service.get_file_content(file['id'])
                if content:
                    analysis = await local_llm.analyze_text(content)
                    if analysis.is_sensitive:
                        # Increment sensitive document count
                        response[age_category]["total_sensitive"] += 1
                        
                        # Add file to appropriate sensitive categories
                        sensitive_file = {
                            'file': file,
                            'confidence': analysis.confidence,
                            'explanation': analysis.explanation,
                            'categories': analysis.categories  # List of detected sensitive categories
                        }
                        
                        # Add to each detected sensitive category
                        for category in analysis.categories:
                            if category in response[age_category]["sensitive_info"]:
                                response[age_category]["sensitive_info"][category].append(sensitive_file)
                            
            except Exception as e:
                logger.error(f"Error analyzing file {file['name']}: {e}")
                continue
        
        response["scan_complete"] = True
        return response
        
    except ValueError as e:
        logger.error(f"Value error in analyze_directory: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except asyncio.TimeoutError:
        logger.error("Timeout analyzing directory")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Operation timed out"
        )
    except Exception as e:
        logger.error(f"Error analyzing directory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

def categorize_file_type(file: Dict) -> str:
    """
    Categorize a file based on its MIME type or extension.
    Returns one of: documents, spreadsheets, presentations, pdfs, images, others
    """
    mime_type = file.get('mimeType', '').lower()
    name = file.get('name', '').lower()
    
    if 'document' in mime_type or name.endswith(('.doc', '.docx')):
        return "documents"
    elif 'spreadsheet' in mime_type or name.endswith(('.xls', '.xlsx', '.csv')):
        return "spreadsheets"
    elif 'presentation' in mime_type or name.endswith(('.ppt', '.pptx')):
        return "presentations"
    elif 'pdf' in mime_type or name.endswith('.pdf'):
        return "pdfs"
    elif ('image' in mime_type or 
          any(name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp'])):
        return "images"
    else:
        return "others"

@router.get("/directories/{folder_id}/categorize")
async def categorize_directory(folder_id: str, page_size: int = 100):
    """Get categorized files in a specific directory."""
    if not drive_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please authenticate first.")
    try:
        categories = drive_service.categorize_directory(folder_id, page_size)
        return {
            "folder_id": folder_id,
            "categories": categories
        }
    except Exception as e:
        logger.error(f"Error categorizing directory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/directories", response_model=List[Dict])
async def list_directories(
    drive_service: GoogleDriveService = Depends(get_current_user)
) -> List[Dict]:
    """List all top-level directories in Google Drive."""
    try:
        return await drive_service.list_directories()
    except ValueError as e:
        logger.error(f"Value error in list_directories: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except asyncio.TimeoutError:
        logger.error("Timeout listing directories")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Operation timed out"
        )
    except Exception as e:
        logger.error(f"Error listing directories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 