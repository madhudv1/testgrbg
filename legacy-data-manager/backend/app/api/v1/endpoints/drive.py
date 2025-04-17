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
        
        # Initialize age category counters
        age_categories = {
            'lessThanOneYear': {'count': 0, 'types': {}, 'risks': {}},
            'oneToThreeYears': {'count': 0, 'types': {}, 'risks': {}},
            'moreThanThreeYears': {'count': 0, 'types': {}, 'risks': {}}
        }
        
        # Initialize file type counters for each age category
        for age_category in age_categories.values():
            age_category['types'] = {
                'documents': {'count': 0, 'size': 0},
                'spreadsheets': {'count': 0, 'size': 0},
                'presentations': {'count': 0, 'size': 0},
                'pdfs': {'count': 0, 'size': 0},
                'images': {'count': 0, 'size': 0},
                'others': {'count': 0, 'size': 0}
            }
            # Add dummy PII data
            age_category['risks'] = {
                'pii': {'count': 0, 'size': 0, 'percentage': 0},
                'financial': {'count': 0, 'size': 0, 'percentage': 0},
                'legal': {'count': 0, 'size': 0, 'percentage': 0},
                'confidential': {'count': 0, 'size': 0, 'percentage': 0}
            }
        
        for file in files:
            # Calculate age and determine category
            modified_time = datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
            file_size = int(file.get('size', 0))
            
            if modified_time > one_year_ago:
                age_category = age_categories['lessThanOneYear']
            elif modified_time > three_years_ago:
                age_category = age_categories['oneToThreeYears']
            else:
                age_category = age_categories['moreThanThreeYears']
            
            age_category['count'] += 1
            
            # Calculate file type distribution
            mime_type = file.get('mimeType', '')
            
            if mime_type == 'application/vnd.google-apps.document':
                age_category['types']['documents']['count'] += 1
                age_category['types']['documents']['size'] += file_size
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                age_category['types']['spreadsheets']['count'] += 1
                age_category['types']['spreadsheets']['size'] += file_size
            elif mime_type == 'application/vnd.google-apps.presentation':
                age_category['types']['presentations']['count'] += 1
                age_category['types']['presentations']['size'] += file_size
            elif mime_type == 'application/pdf':
                age_category['types']['pdfs']['count'] += 1
                age_category['types']['pdfs']['size'] += file_size
            elif mime_type.startswith('image/'):
                age_category['types']['images']['count'] += 1
                age_category['types']['images']['size'] += file_size
            else:
                age_category['types']['others']['count'] += 1
                age_category['types']['others']['size'] += file_size
        
        # Calculate percentages for each age category
        total_files = len(files)
        if total_files > 0:
            for age_category in age_categories.values():
                # Calculate type percentages
                for type_data in age_category['types'].values():
                    if age_category['count'] > 0:
                        type_data['percentage'] = round((type_data['count'] / age_category['count']) * 100, 1)
                    else:
                        type_data['percentage'] = 0
                
                # Add dummy PII percentages (random values for now)
                age_category['risks']['pii']['percentage'] = round(30 + (age_category['count'] % 20), 1)
                age_category['risks']['financial']['percentage'] = round(20 + (age_category['count'] % 15), 1)
                age_category['risks']['legal']['percentage'] = round(15 + (age_category['count'] % 10), 1)
                age_category['risks']['confidential']['percentage'] = round(10 + (age_category['count'] % 5), 1)
        
        return {
            "folder_id": folder_id,
            "total_files": total_files,
            "ageDistribution": {
                "lessThanOneYear": {
                    "count": age_categories['lessThanOneYear']['count'],
                    "types": age_categories['lessThanOneYear']['types'],
                    "risks": age_categories['lessThanOneYear']['risks']
                },
                "oneToThreeYears": {
                    "count": age_categories['oneToThreeYears']['count'],
                    "types": age_categories['oneToThreeYears']['types'],
                    "risks": age_categories['oneToThreeYears']['risks']
                },
                "moreThanThreeYears": {
                    "count": age_categories['moreThanThreeYears']['count'],
                    "types": age_categories['moreThanThreeYears']['types'],
                    "risks": age_categories['moreThanThreeYears']['risks']
                }
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