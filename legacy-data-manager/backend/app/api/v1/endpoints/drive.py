from fastapi import APIRouter, HTTPException
from typing import Dict, List
from ....services.google_drive import GoogleDriveService
from ....core.config import settings
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
drive_service = GoogleDriveService()

@router.get("/auth/url")
async def get_auth_url():
    """Get the Google OAuth2 authorization URL."""
    try:
        auth_url = drive_service.get_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/callback")
async def auth_callback(code: str):
    """Handle the OAuth2 callback and get credentials."""
    try:
        credentials = drive_service.get_credentials_from_code(code)
        return {"message": "Successfully authenticated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/status")
async def get_auth_status():
    """Check if the service is authenticated."""
    return {"authenticated": drive_service.is_authenticated()}

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