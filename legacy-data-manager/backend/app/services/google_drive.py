from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class GoogleDriveService:
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file'
    ]

    def __init__(self):
        self.credentials = None
        self.service = None

    def is_authenticated(self) -> bool:
        """Check if the service is authenticated."""
        return self.credentials is not None and not self.credentials.expired

    def get_auth_url(self) -> str:
        """Generate the authorization URL for Google OAuth2."""
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        }
        
        flow = Flow.from_client_config(
            client_config=client_config,
            scopes=self.SCOPES
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return auth_url

    def get_credentials_from_code(self, code: str) -> Credentials:
        """Get credentials from authorization code."""
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        }
        
        flow = Flow.from_client_config(
            client_config=client_config,
            scopes=self.SCOPES
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        self.credentials = flow.credentials
        return self.credentials

    def build_service(self):
        """Build the Google Drive service."""
        if not self.is_authenticated():
            raise ValueError("Not authenticated. Please authenticate first.")
        self.service = build('drive', 'v3', credentials=self.credentials)

    def list_files(self, page_size: int = 100) -> List[Dict]:
        """List files from Google Drive."""
        if not self.service:
            self.build_service()
        
        results = self.service.files().list(
            pageSize=page_size,
            fields="files(id, name, mimeType, modifiedTime, owners, lastModifyingUser)"
        ).execute()
        
        return results.get('files', [])

    def get_file_metadata(self, file_id: str) -> Dict:
        """Get detailed metadata for a specific file."""
        if not self.service:
            self.build_service()
        
        return self.service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, modifiedTime, owners, lastModifyingUser, createdTime"
        ).execute()

    def get_inactive_files(self, months_threshold: int = 12) -> List[Dict]:
        """Get files that haven't been modified in the specified number of months."""
        if not self.service:
            self.build_service()
        
        # Calculate the cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=months_threshold * 30)
        cutoff_date_str = cutoff_date.isoformat() + 'Z'
        
        logger.debug(f"Querying for files modified before: {cutoff_date_str}")
        
        # Query for files modified before the cutoff date
        try:
            results = self.service.files().list(
                q=f"modifiedTime < '{cutoff_date_str}'",
                fields="files(id, name, mimeType, modifiedTime, owners, lastModifyingUser, createdTime)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            logger.debug(f"Found {len(files)} inactive files")
            return files
        except Exception as e:
            logger.error(f"Error in get_inactive_files: {str(e)}", exc_info=True)
            raise 