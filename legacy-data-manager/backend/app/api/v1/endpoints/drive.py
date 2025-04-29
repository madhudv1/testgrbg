from fastapi import APIRouter, HTTPException, Request, Depends, status
from typing import Dict, List, Optional
from ....services.google_drive import GoogleDriveService
from ....core.config import settings
import logging
from datetime import datetime, timezone, timedelta
from fastapi.responses import RedirectResponse
import json
import uuid
import asyncio
from ....core.auth import get_current_user
from ....services.file_scanner_with_json import scan_files
from ....services.scan_cache_service import ScanCacheService
from asyncio import Lock, TimeoutError

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
drive_service = GoogleDriveService()
scan_cache = ScanCacheService()

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

@router.post("/directories/{folder_id}/analyze")
async def analyze_directory(
    folder_id: str,
    drive_service: GoogleDriveService = Depends(get_current_user),
):
    try:
        # Check cache first
        cached_result = scan_cache.get_cached_result(folder_id)
        if cached_result:
            logger.info(f"Using cached result for directory {folder_id}")
            return cached_result

        # Initialize response structure
        response = initialize_response_structure()
        
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
        
        # Process files using the scanner
        try:
            response = await scan_files(source='gdrive', path_or_drive_id=folder_id)
            response["scan_complete"] = True
            
            # Cache the results
            scan_cache.update_cache(folder_id, response)
            logger.info(f"Cached scan results for directory {folder_id}")
            
            return response
        except Exception as e:
            logger.error(f"Error scanning files: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error scanning files: {str(e)}"
            )
        
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
    """List all directories in the user's drive."""
    try:
        directories = await drive_service.list_directories()
        return directories
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