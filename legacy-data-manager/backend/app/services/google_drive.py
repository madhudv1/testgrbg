from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from ..core.config import settings
import logging
import io
import PyPDF2
import os
import json
import pickle
import asyncio

logger = logging.getLogger(__name__)

class GoogleDriveService:
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file'
    ]
    TOKEN_FILE = 'token.pickle'

    def __init__(self):
        self.credentials = None
        self.service = None
        logger.info(f"Token file path: {self.TOKEN_FILE}")

    async def ensure_service(self):
        """Ensure the service is built with timeout."""
        if not self.service:
            try:
                async with asyncio.timeout(5):  # 5 second timeout
                    await asyncio.to_thread(self._build_service)
            except asyncio.TimeoutError:
                logger.error("Timeout building Google Drive service")
                raise ValueError("Timeout building service")
            except Exception as e:
                logger.error(f"Error building service: {e}")
                raise

    def _build_service(self):
        """Internal method to build the service."""
        try:
            credentials = self.load_credentials()
            if not credentials:
                raise ValueError("Not authenticated. Please authenticate first.")
            
            # Validate refresh token exists
            if not credentials.refresh_token:
                logger.error("Credentials missing refresh token")
                raise ValueError("Invalid credentials: missing refresh token")
            
            # Check if expired and try to refresh
            if credentials.expired:
                try:
                    credentials.refresh(Request())
                    self.save_credentials(credentials)
                except Exception as e:
                    logger.error(f"Failed to refresh expired credentials: {e}")
                    raise ValueError("Failed to refresh credentials")
                
            self.service = build('drive', 'v3', credentials=credentials)
            return self.service
        except Exception as e:
            logger.error(f"Error building service: {e}")
            raise

    async def is_authenticated(self):
        """Check if we have valid credentials."""
        try:
            credentials = self.load_credentials()
            
            if not credentials:
                logger.debug("No credentials found")
                return False
                
            # Validate refresh token exists
            if not credentials.refresh_token:
                logger.error("Credentials missing refresh token")
                return False
                
            # Check if expired and try to refresh
            if credentials.expired:
                logger.debug("Credentials expired, attempting refresh")
                try:
                    async with asyncio.timeout(5):  # 5 second timeout
                        await asyncio.to_thread(lambda: credentials.refresh(Request()))
                        await asyncio.to_thread(self.save_credentials, credentials)
                        logger.debug("Successfully refreshed credentials")
                except asyncio.TimeoutError:
                    logger.error("Timeout refreshing credentials")
                    return False
                except Exception as e:
                    logger.error(f"Failed to refresh expired credentials: {e}")
                    return False
            
            logger.debug("Authentication check successful")
            return True
        except Exception as e:
            logger.error(f"Error checking authentication: {e}", exc_info=True)
            return False

    async def list_files(self, page_size: int = 100) -> List[Dict]:
        """List files from Google Drive."""
        await self.ensure_service()
        
        try:
            async with asyncio.timeout(10):  # 10 second timeout
                results = await asyncio.to_thread(
                    lambda: self.service.files().list(
                        pageSize=page_size,
                        fields="files(id, name, mimeType, modifiedTime, owners, lastModifyingUser)"
                    ).execute()
                )
            return results.get('files', [])
        except asyncio.TimeoutError:
            logger.error("Timeout listing files")
            raise ValueError("Timeout listing files")
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise

    async def list_directories(self, page_size: int = 100) -> List[Dict]:
        """List top-level directories (folders) owned by the authenticated user from Google Drive."""
        try:
            await self.ensure_service()
            
            query = "mimeType='application/vnd.google-apps.folder' and 'me' in owners and 'root' in parents and trashed = false"
            
            async with asyncio.timeout(10):  # 10 second timeout
                results = await asyncio.to_thread(
                    lambda: self.service.files().list(
                        q=query,
                        pageSize=page_size,
                        fields="files(id, name, mimeType, modifiedTime, owners, lastModifyingUser, createdTime)"
                    ).execute()
                )
            
            return results.get('files', [])
        except asyncio.TimeoutError:
            logger.error("Timeout listing directories")
            raise ValueError("Timeout listing directories")
        except Exception as e:
            logger.error(f"Error listing directories: {e}")
            raise

    def load_credentials(self):
        """Load credentials from token file."""
        if not os.path.exists('token.pickle'):
            return None
        
        try:
            with open('token.pickle', 'rb') as token:
                credentials = pickle.load(token)
                
                # Validate credentials have refresh token
                if not credentials.refresh_token:
                    logger.error("Loaded credentials missing refresh token")
                    return None
                    
                # Check if credentials are expired and can be refreshed
                if credentials.expired and credentials.refresh_token:
                    try:
                        credentials.refresh(Request())
                        # Save refreshed credentials
                        self.save_credentials(credentials)
                    except Exception as e:
                        logger.error(f"Failed to refresh credentials: {e}")
                        return None
                        
                return credentials
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return None

    def save_credentials(self, credentials):
        """Save credentials to token file."""
        try:
            # Validate credentials have refresh token before saving
            if not credentials.refresh_token:
                logger.error("Cannot save credentials - missing refresh token")
                return False
                
            with open('token.pickle', 'wb') as token:
                pickle.dump(credentials, token)
            return True
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            return False

    async def get_auth_url(self, state: str = None) -> str:
        """Generate the authorization URL for Google OAuth2."""
        logger.debug("Generating auth URL")
        try:
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
                prompt='consent',
                include_granted_scopes='true',
                state=state
            )
            logger.debug(f"Generated auth URL with redirect_uri: {settings.GOOGLE_REDIRECT_URI}")
            return auth_url
        except Exception as e:
            logger.error(f"Error generating auth URL: {e}", exc_info=True)
            raise

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
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Validate we have a refresh token
            if not credentials.refresh_token:
                logger.error("No refresh token received from Google OAuth flow")
                raise ValueError("No refresh token received. Please try again.")
                
            # Save the credentials
            if not self.save_credentials(credentials):
                raise ValueError("Failed to save credentials")
                
            return credentials
        except Exception as e:
            logger.error(f"Error getting credentials from code: {e}")
            raise

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

    async def list_directory(self, folder_id: str, page_size: int = 100, recursive: bool = False) -> List[Dict]:
        """List files in a specific directory."""
        logger.info(f"Attempting to list directory with ID: {folder_id} (recursive: {recursive})")
        await self.ensure_service()
        
        if recursive:
            return await self._recursive_list_directory(folder_id, page_size)
        
        query = f"'{folder_id}' in parents and trashed = false"
        try:
            results = await asyncio.to_thread(
                lambda: self.service.files().list(
            q=query,
            pageSize=page_size,
            fields="files(id, name, mimeType, modifiedTime, owners, lastModifyingUser, createdTime, size)"
        ).execute()
            )
            logger.info(f"Successfully listed directory {folder_id}")
            return results.get('files', [])
        except HttpError as error:
            logger.error(f"Google Drive API error listing directory {folder_id}: {error}")
            raise

    async def _recursive_list_directory(self, folder_id: str, page_size: int = 100) -> List[Dict]:
        """Recursively list all files in a directory and its subdirectories."""
        all_files = []
        
        # Get files in current directory
        try:
            files = await self.list_directory(folder_id, page_size, recursive=False)
            
            # Process each file/folder
            for file in files:
                if file['mimeType'] == 'application/vnd.google-apps.folder':
                    # Recursively get files from subdirectory
                    logger.info(f"Recursively listing subdirectory: {file['name']} ({file['id']})")
                    sub_files = await self._recursive_list_directory(file['id'], page_size)
                    all_files.extend(sub_files)
                else:
                    all_files.append(file)
            
            return all_files
            
        except Exception as e:
            logger.error(f"Error in recursive directory listing for folder {folder_id}: {e}")
            raise

    async def get_file_content(self, file_id: str) -> Optional[str]:
        """Get the content of a file from Google Drive."""
        try:
            # Get the file metadata first
            file = await self.service.files().get(fileId=file_id, 
                                                fields='mimeType').execute()
            
            # Handle Google Workspace files
            if mime_type.startswith('application/vnd.google-apps.'):
                if mime_type == 'application/vnd.google-apps.document':
                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(
                                self.service.files().export(
                                    fileId=file_id,
                                    mimeType='text/plain'
                                ).execute
                            ),
                            timeout=timeout
                        )
                        return response if isinstance(response, str) else response.decode('utf-8')
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout exporting Google Doc {file_id}")
                        return ""
                    except Exception as e:
                        logger.error(f"Error exporting Google Doc {file_id}: {e}")
                        return ""
                
                elif mime_type == 'application/vnd.google-apps.spreadsheet':
                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(
                                self.service.files().export(
                                    fileId=file_id,
                                    mimeType='text/csv'
                                ).execute
                            ),
                            timeout=timeout
                        )
                        return response if isinstance(response, str) else response.decode('utf-8')
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout exporting Google Spreadsheet {file_id}")
                        return ""
                    except Exception as e:
                        logger.error(f"Error exporting Google Spreadsheet {file_id}: {e}")
                        return ""
                
                elif mime_type == 'application/vnd.google-apps.presentation':
                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(
                                self.service.files().export(
                                    fileId=file_id,
                                    mimeType='text/plain'
                                ).execute
                            ),
                            timeout=timeout
                        )
                        return response if isinstance(response, str) else response.decode('utf-8')
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout exporting Google Presentation {file_id}")
                        return ""
                    except Exception as e:
                        logger.error(f"Error exporting Google Presentation {file_id}: {e}")
                        return ""
                
                else:
                    logger.warning(f"Unsupported Google Workspace type: {mime_type}")
                    return ""
            
            # For non-Google Workspace files, check size first
            file_size = int(file_metadata.get('size', 0))
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                logger.warning(f"File {file_id} is too large ({file_size} bytes)")
                return ""
            
            # Handle regular files
            if mime_type == 'application/pdf':
                try:
                    pdf_content = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.service.files().get_media(fileId=file_id).execute
                        ),
                        timeout=timeout
                    )
                    
                    # Convert PDF to text
                    pdf_file = io.BytesIO(pdf_content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Extract text from all pages
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    
                    return text
                except asyncio.TimeoutError:
                    logger.error(f"Timeout downloading PDF {file_id}")
                    return ""
                except Exception as e:
                    logger.error(f"Error processing PDF file: {str(e)}")
                    return ""
                    
            elif mime_type.startswith('text/'):
                try:
                    content = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.service.files().get_media(fileId=file_id).execute
                        ),
                        timeout=timeout
                    )
                    return content.decode('utf-8')
                except asyncio.TimeoutError:
                    logger.error(f"Timeout downloading text file {file_id}")
                    return ""
                except UnicodeDecodeError:
                    logger.error(f"Error decoding text file {file_id}")
                    return ""
            
            elif mime_type.startswith('image/'):
                logger.info(f"Skipping image file {file_id} - OCR not yet implemented")
                return ""
                
            else:
                logger.warning(f"Unsupported mime type: {mime_type}")
                return ""
                
        except Exception as e:
            logger.error(f"Error getting file content: {str(e)}")
            return ""

    def get_file_size(self, file_id: str) -> int:
        """Get the size of a file in bytes."""
        if not self.service:
            self.build_service()
        
        try:
            file_metadata = self.get_file_metadata(file_id)
            return int(file_metadata.get('size', 0))
        except Exception as e:
            logger.error(f"Error getting file size: {str(e)}")
            raise 

    def categorize_directory(self, folder_id: str, page_size: int = 100) -> Dict:
        """
        List and categorize files in a specific directory.
        Returns a dictionary with categorized files.
        """
        logger.info(f"Starting categorization for folder ID: {folder_id}")
        if not self.service:
            self.build_service()
        
        try:
            # Get all files in the directory
            logger.info(f"Calling list_directory for folder ID: {folder_id}")
            files = self.list_directory(folder_id, page_size)
            logger.info(f"list_directory returned {len(files)} files for folder ID: {folder_id}")
        except Exception as e:
            logger.error(f"Error occurred during list_directory call within categorize_directory for folder ID {folder_id}: {e}", exc_info=True)
            raise 

        # Initialize categories
        categories = {
            'documents': [],
            'spreadsheets': [],
            'presentations': [],
            'pdfs': [],
            'images': [],
            'others': [],
            'recent': [],  # Files modified in last 30 days
            'large_files': [],  # Files larger than 10MB
            'by_owner': {},  # Files grouped by owner
            'internal': [],  # Files owned by internal users
            'external': [],  # Files owned by external users
            'by_department': {  # Files grouped by department
                'engineering': [],
                'hr': [],
                'finance': [],
                'legal': [],
                'other': []
            }
        }
        
        # --- Make timestamp comparison timezone-aware --- 
        logger.debug(f"Starting categorization loop for {len(files)} files in folder {folder_id}") # Log before loop
        
        # Use timezone.utc to make current_time offset-aware
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc) 
        thirty_days_ago = current_time - timedelta(days=30)
        logger.debug(f"Comparison timestamp (30 days ago, UTC): {thirty_days_ago}")
        
        for index, file in enumerate(files):
            try:
                # Get file metadata
                mime_type = file.get('mimeType', '')
                # modified_time is already offset-aware due to .replace('Z', '+00:00')
                modified_time = datetime.fromisoformat(file.get('modifiedTime', '').replace('Z', '+00:00')) 
                file_size = int(file.get('size', 0))
                owner = file.get('owners', [{}])[0]
                owner_email = owner.get('emailAddress', '').lower()
                owner_name = owner.get('displayName', 'Unknown')
                
                # Categorize by file type
                if mime_type == 'application/vnd.google-apps.document':
                    categories['documents'].append(file)
                elif mime_type == 'application/vnd.google-apps.spreadsheet':
                    categories['spreadsheets'].append(file)
                elif mime_type == 'application/vnd.google-apps.presentation':
                    categories['presentations'].append(file)
                elif mime_type == 'application/pdf':
                    categories['pdfs'].append(file)
                elif mime_type.startswith('image/'):
                    categories['images'].append(file)
                else:
                    categories['others'].append(file)
                
                # Categorize by modification time (NOW COMPARING aware vs aware)
                if modified_time > thirty_days_ago:
                    categories['recent'].append(file)
                
                # Categorize by size
                if file_size > 10 * 1024 * 1024:  # 10MB
                    categories['large_files'].append(file)
                
                # Categorize by owner
                if owner_name not in categories['by_owner']:
                    categories['by_owner'][owner_name] = []
                categories['by_owner'][owner_name].append(file)
                
                # Categorize internal/external based on email domain
                if '@grbg.com' in owner_email:
                    categories['internal'].append(file)
                else:
                    categories['external'].append(file)
                
                # Categorize by department based on email patterns
                if any(domain in owner_email for domain in ['@grbg.com']):
                    if any(term in owner_email for term in ['eng', 'dev', 'engineering', 'developer']):
                        categories['by_department']['engineering'].append(file)
                    elif any(term in owner_email for term in ['hr', 'human.resources']):
                        categories['by_department']['hr'].append(file)
                    elif any(term in owner_email for term in ['finance', 'accounting']):
                        categories['by_department']['finance'].append(file)
                    elif any(term in owner_email for term in ['legal', 'law']):
                        categories['by_department']['legal'].append(file)
                    else:
                        categories['by_department']['other'].append(file)
                else:
                    categories['by_department']['other'].append(file)
                
                logger.debug(f"Categorized file {index + 1}/{len(files)}: {file.get('name', 'N/A')}") # Log inside loop
            except Exception as loop_error:
                logger.error(f"Error categorizing file {file.get('id', 'N/A')} ({file.get('name', 'N/A')}) in folder {folder_id}: {loop_error}", exc_info=True)
                # Optionally add the problematic file to an 'errors' category
                if 'errors' not in categories:
                    categories['errors'] = []
                categories['errors'].append({'file_id': file.get('id'), 'name': file.get('name'), 'error': str(loop_error)}) 
                # Continue to the next file instead of stopping the whole categorization
                continue
        
        # Add summary statistics
        categories['summary'] = {
            'total_files': len(files),
            'total_size': sum(int(f.get('size', 0)) for f in files),
            'by_type': {
                'documents': len(categories['documents']),
                'spreadsheets': len(categories['spreadsheets']),
                'presentations': len(categories['presentations']),
                'pdfs': len(categories['pdfs']),
                'images': len(categories['images']),
                'others': len(categories['others'])
            },
            'recent_files': len(categories['recent']),
            'large_files': len(categories['large_files']),
            'owners': len(categories['by_owner']),
            'internal_files': len(categories['internal']),
            'external_files': len(categories['external']),
            'by_department': {
                dept: len(files) for dept, files in categories['by_department'].items()
            }
        }
        
        logger.info(f"Finished categorization for folder ID: {folder_id}")
        return categories 