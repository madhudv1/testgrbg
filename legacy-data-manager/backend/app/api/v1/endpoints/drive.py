from fastapi import APIRouter, HTTPException
from typing import Dict, List
from ....services.google_drive import GoogleDriveService
from ....core.config import settings
import logging
from ....services.genai_service import GenAIService
from datetime import datetime, timezone, timedelta

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
        
        # Calculate age distribution
        one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
        three_years_ago = datetime.now(timezone.utc) - timedelta(days=365*3)
        
        less_than_one_year = 0
        one_to_three_years = 0
        more_than_three_years = 0
        
        # Initialize file type counters
        file_types = {
            'documents': {'count': 0, 'size': 0},
            'spreadsheets': {'count': 0, 'size': 0},
            'presentations': {'count': 0, 'size': 0},
            'pdfs': {'count': 0, 'size': 0},
            'images': {'count': 0, 'size': 0},
            'others': {'count': 0, 'size': 0}
        }
        
        # Initialize owner statistics
        owners = {}
        internal_count = 0
        external_count = 0
        
        for file in files:
            # Calculate age distribution
            modified_time = datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
            if modified_time > one_year_ago:
                less_than_one_year += 1
            elif modified_time > three_years_ago:
                one_to_three_years += 1
            else:
                more_than_three_years += 1
                
            # Calculate file type distribution
            mime_type = file.get('mimeType', '')
            file_size = int(file.get('size', 0))
            
            if mime_type == 'application/vnd.google-apps.document':
                file_types['documents']['count'] += 1
                file_types['documents']['size'] += file_size
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                file_types['spreadsheets']['count'] += 1
                file_types['spreadsheets']['size'] += file_size
            elif mime_type == 'application/vnd.google-apps.presentation':
                file_types['presentations']['count'] += 1
                file_types['presentations']['size'] += file_size
            elif mime_type == 'application/pdf':
                file_types['pdfs']['count'] += 1
                file_types['pdfs']['size'] += file_size
            elif mime_type.startswith('image/'):
                file_types['images']['count'] += 1
                file_types['images']['size'] += file_size
            else:
                file_types['others']['count'] += 1
                file_types['others']['size'] += file_size
            
            # Calculate owner distribution
            owner = file.get('owners', [{}])[0]
            owner_email = owner.get('emailAddress', '').lower()
            owner_name = owner.get('displayName', 'Unknown')
            
            if owner_name not in owners:
                owners[owner_name] = {
                    'count': 0,
                    'size': 0,
                    'email': owner_email,
                    'isInternal': '@grbg.com' in owner_email
                }
            
            owners[owner_name]['count'] += 1
            owners[owner_name]['size'] += file_size
            
            # Count internal vs external
            if '@grbg.com' in owner_email:
                internal_count += 1
            else:
                external_count += 1
        
        total_files = len(files)
        if total_files > 0:
            less_than_one_year_pct = (less_than_one_year / total_files) * 100
            one_to_three_years_pct = (one_to_three_years / total_files) * 100
            more_than_three_years_pct = (more_than_three_years / total_files) * 100
        else:
            less_than_one_year_pct = 0
            one_to_three_years_pct = 0
            more_than_three_years_pct = 0
        
        # Convert owners dict to sorted list by file count
        owners_list = [
            {**stats, 'name': name}
            for name, stats in owners.items()
        ]
        owners_list.sort(key=lambda x: x['count'], reverse=True)
        
        return {
            "folder_id": folder_id,
            "total_files": total_files,
            "ageDistribution": {
                "lessThanOneYear": round(less_than_one_year_pct, 1),
                "oneToThreeYears": round(one_to_three_years_pct, 1),
                "moreThanThreeYears": round(more_than_three_years_pct, 1)
            },
            "lessThanOneYearCount": less_than_one_year,
            "oneToThreeYearsCount": one_to_three_years,
            "moreThanThreeYearsCount": more_than_three_years,
            "fileTypes": file_types,
            "ownerStats": {
                "owners": owners_list,
                "internalCount": internal_count,
                "externalCount": external_count,
                "totalOwners": len(owners)
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