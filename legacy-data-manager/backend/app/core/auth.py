from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from ..services.google_drive import GoogleDriveService
import logging

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> GoogleDriveService:
    """
    FastAPI dependency that validates the user's authentication and returns a GoogleDriveService instance.
    If no token is provided or authentication fails, returns an unauthenticated service instance.
    """
    drive_service = GoogleDriveService()
    
    try:
        # Check if already authenticated
        is_auth = await drive_service.is_authenticated()
        if not is_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return drive_service
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) 