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
from app.services.rule_based_classifier import RuleBasedClassifier
from asyncio import Lock, TimeoutError

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
drive_service = GoogleDriveService()
genai_service = GenAIService()

# Initialize services
local_llm = LocalLLMService()
rate_limiter = LLMRateLimiter()

def determine_file_type(file: Dict) -> str:
    """
    Determine the type of file based on its MIME type.
    Returns one of: "documents", "spreadsheets", "presentations", "pdfs", "images", "others"
    """
    mime_type = file.get('mimeType', '')
    
    if mime_type == 'application/pdf':
        return 'pdfs'
    elif mime_type.startswith('image/'):
        return 'images'
    elif mime_type in ['application/vnd.google-apps.document', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        return 'documents'
    elif mime_type in ['application/vnd.google-apps.spreadsheet', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
        return 'spreadsheets'
    elif mime_type in ['application/vnd.google-apps.presentation', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
        return 'presentations'
    else:
        return 'others'

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

def initialize_response_structure():
    return {
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
                "pii": [],
                "financial": [],
                "legal": [],
                "confidential": []
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
                "pii": [],
                "financial": [],
                "legal": [],
                "confidential": []
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
                "pii": [],
                "financial": [],
                "legal": [],
                "confidential": []
            }
        },
        "scan_complete": False,
        "processed_files": 0,
        "total_files": 0,
        "failed_files": []
    }

async def process_file(file: Dict, drive_service: GoogleDriveService, classifier: RuleBasedClassifier, response: Dict) -> None:
    """Process a single file and update the response dictionary"""
    try:
        # First, categorize by age and type
        age_category = categorize_file_by_age(file)
        file_type = determine_file_type(file)
        
        # Update counts
        response[age_category]["total_documents"] += 1
        response[age_category]["file_types"][file_type].append({
            "id": file.get("id"),
            "name": file.get("name"),
            "mimeType": file.get("mimeType"),
            "modifiedTime": file.get("modifiedTime")
        })
        response["processed_files"] += 1
        
        # Only process content for specific file types
        if file_type not in ["documents", "spreadsheets", "presentations", "pdfs", "images"]:
            return

        # Try to get content with timeout
        content = None
        try:
            content = await asyncio.wait_for(
                drive_service.get_file_content(file['id']),
                timeout=10.0  # 10 second timeout for content retrieval
            )
        except (TimeoutError, Exception) as e:
            logger.warning(f"Could not get content for file {file['name']}: {e}")
            response["failed_files"].append({
                "name": file["name"],
                "error": str(e)
            })
            return

        # Skip analysis if we couldn't get content
        if content is None:
            logger.warning(f"No content retrieved for file {file['name']}")
            return

        # Analyze with timeout
        try:
            analysis = await asyncio.wait_for(
                classifier.analyze_document(file['name'], file['mimeType'], content),
                timeout=5.0  # 5 second timeout for analysis
            )
            
            # Clear content from memory
            del content
            
        except (TimeoutError, Exception) as e:
            logger.error(f"Error analyzing file {file['name']}: {e}")
            response["failed_files"].append({
                "name": file["name"],
                "error": str(e)
            })
            return

        # Process analysis results
        if analysis and analysis.get('confidence_score', 0) > 0.7:
            response[age_category]["total_sensitive"] += 1
            sensitive_file = {
                'file': {
                    "id": file.get("id"),
                    "name": file.get("name"),
                    "mimeType": file.get("mimeType"),
                    "modifiedTime": file.get("modifiedTime")
                },
                'confidence': analysis.get('confidence_score', 0),
                'explanation': analysis.get('explanation', ''),
                'categories': analysis.get('key_topics', []),
                'queued_for_analysis': analysis.get('queued_for_analysis', False)
            }
            
            category_mapping = {
                'HR Documents': 'pii',
                'Financial Documents': 'financial',
                'Legal Documents': 'legal',
                'Technical Documents': 'confidential'
            }
            
            primary_category = analysis.get('primary_category', '')
            if primary_category in category_mapping:
                category = category_mapping[primary_category]
                if category in response[age_category]["sensitive_info"]:
                    response[age_category]["sensitive_info"][category].append(sensitive_file)

    except Exception as e:
        logger.error(f"Error processing file {file.get('name', 'unknown')}: {e}")
        response["failed_files"].append({
            "name": file.get("name", "unknown"),
            "error": str(e)
        })

async def process_batch(files: List[Dict], drive_service: GoogleDriveService, 
                       classifier: RuleBasedClassifier, response: Dict) -> None:
    """Process a batch of files concurrently"""
    tasks = []
    for file in files:
        task = asyncio.create_task(process_file(file, drive_service, classifier, response))
        tasks.append(task)
    await asyncio.gather(*tasks, return_exceptions=True)

@router.post("/directories/{folder_id}/analyze")
async def analyze_directory(
    folder_id: str,
    drive_service: GoogleDriveService = Depends(get_current_user),
):
    try:
        response = initialize_response_structure()
        classifier = RuleBasedClassifier()
        
        # Get files in directory
        try:
            files = await drive_service.list_directory(folder_id, recursive=True)
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error listing directory: {str(e)}"
            )
            
        if not files:
            return response
            
        # Set total files count
        response["total_files"] = len(files)
        
        # Process files in smaller batches
        batch_size = 2  # Reduced batch size
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            try:
                await asyncio.wait_for(
                    process_batch(batch, drive_service, classifier, response),
                    timeout=20.0  # Reduced timeout per batch
                )
            except TimeoutError:
                logger.error(f"Timeout processing batch starting at index {i}")
                for file in batch:
                    response["failed_files"].append({
                        "name": file.get("name", "unknown"),
                        "error": "Batch processing timeout"
                    })
            except Exception as e:
                logger.error(f"Error processing batch starting at index {i}: {e}")
                for file in batch:
                    response["failed_files"].append({
                        "name": file.get("name", "unknown"),
                        "error": str(e)
                    })
            
            # Force garbage collection after each batch
            import gc
            gc.collect()
        
        response["scan_complete"] = True
        return response
        
    except Exception as e:
        logger.error(f"Error analyzing directory: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing directory: {str(e)}"
        )

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