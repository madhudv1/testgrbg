from sqlalchemy.orm import Session
from ..db.models import SlackUser
from ..core.config import settings
from .google_drive import GoogleDriveService
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SlackAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.drive_service = GoogleDriveService()
        
    def get_auth_url(self, slack_user_id: str, email: str) -> str:
        """Get Google Drive authentication URL for a Slack user"""
        # Check if user already exists
        user = self.db.query(SlackUser).filter(SlackUser.slack_user_id == slack_user_id).first()
        if not user:
            user = SlackUser(slack_user_id=slack_user_id, email=email)
            self.db.add(user)
            self.db.commit()
            
        return self.drive_service.get_auth_url()
        
    def handle_auth_callback(self, code: str, slack_user_id: str) -> bool:
        """Handle Google Drive authentication callback for a Slack user"""
        try:
            # Get tokens from Google
            tokens = self.drive_service.handle_auth_callback(code)
            
            # Update user with new tokens
            user = self.db.query(SlackUser).filter(SlackUser.slack_user_id == slack_user_id).first()
            if user:
                user.google_drive_token = tokens["access_token"]
                user.google_drive_refresh_token = tokens.get("refresh_token")
                user.token_expires_at = datetime.now() + timedelta(seconds=tokens["expires_in"])
                self.db.commit()
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error handling auth callback: {str(e)}")
            return False
            
    def is_authenticated(self, slack_user_id: str) -> bool:
        """Check if a Slack user is authenticated with Google Drive"""
        user = self.db.query(SlackUser).filter(SlackUser.slack_user_id == slack_user_id).first()
        if not user or not user.google_drive_token:
            return False
            
        # Check if token is expired
        if user.token_expires_at and user.token_expires_at < datetime.now():
            if user.google_drive_refresh_token:
                # Try to refresh the token
                try:
                    tokens = self.drive_service.refresh_token(user.google_drive_refresh_token)
                    user.google_drive_token = tokens["access_token"]
                    user.token_expires_at = datetime.now() + timedelta(seconds=tokens["expires_in"])
                    self.db.commit()
                    return True
                except Exception as e:
                    logger.error(f"Error refreshing token: {str(e)}")
                    return False
            return False
            
        return True 