from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from typing import Dict, List
from ....services.google_drive import GoogleDriveService
from ....core.config import settings
import logging
from ....services.genai_service import GenAIService
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
drive_service = GoogleDriveService()
genai_service = GenAIService()

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
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?auth=success")
    except Exception as e:
        error_message = str(e)
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?auth=error&message={error_message}")

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
async def analyze_directory(folder_id: str):
    """Analyze all files in a directory."""
    if not drive_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please authenticate first.")
    try:
        # Get all files in the directory
        files = drive_service.list_directory(folder_id)
        
        # Initialize counters
        total_files = len(files)
        stale_count = 0
        duplicate_count = 0
        sensitive_count = 0
        less_than_one_year = 0
        one_to_three_years = 0
        more_than_three_years = 0
        
        # Get current time
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Process each file
        for file in files:
            # Convert modified time to datetime
            modified_time_str = file.get('modifiedTime', '')
            if modified_time_str:
                modified_time = datetime.fromisoformat(modified_time_str.replace('Z', '+00:00'))
                age_in_days = (current_time - modified_time).days
                
                # Categorize by age
                if age_in_days < 365:  # Less than 1 year
                    less_than_one_year += 1
                elif age_in_days < 1095:  # 1-3 years (365 * 3)
                    one_to_three_years += 1
                else:  # More than 3 years
                    more_than_three_years += 1
        
        # Calculate percentages
        total_files_with_dates = less_than_one_year + one_to_three_years + more_than_three_years
        if total_files_with_dates > 0:
            less_than_one_year_pct = (less_than_one_year / total_files_with_dates) * 100
            one_to_three_years_pct = (one_to_three_years / total_files_with_dates) * 100
            more_than_three_years_pct = (more_than_three_years / total_files_with_dates) * 100
        else:
            less_than_one_year_pct = 0
            one_to_three_years_pct = 0
            more_than_three_years_pct = 0
        
        return {
            "folder_id": folder_id,
            "total_files": total_files,
            "staleCount": stale_count,
            "duplicateCount": duplicate_count,
            "sensitiveCount": sensitive_count,
            "ageDistribution": {
                "lessThanOneYear": round(less_than_one_year_pct),
                "oneToThreeYears": round(one_to_three_years_pct),
                "moreThanThreeYears": round(more_than_three_years_pct)
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing directory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get("/directories")
async def list_directories(page_size: int = 100):
    """List directories (folders) from Google Drive."""
    if not drive_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please authenticate first.")
    try:
        directories = drive_service.list_directories(page_size)
        return {"directories": directories}
    except Exception as e:
        logger.error(f"Error listing directories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 