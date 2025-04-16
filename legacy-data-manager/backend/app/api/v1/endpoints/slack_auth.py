from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ....db.database import get_db
from ....services.slack_auth import SlackAuthService
from fastapi.responses import RedirectResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_slack_auth_service(db: Session = Depends(get_db)):
    return SlackAuthService(db)

@router.get("/auth/url")
async def get_auth_url(
    slack_user_id: str,
    email: str,
    slack_auth_service: SlackAuthService = Depends(get_slack_auth_service)
):
    """Get Google Drive authentication URL for a Slack user"""
    try:
        auth_url = slack_auth_service.get_auth_url(slack_user_id, email)
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error getting auth URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/callback")
async def handle_auth_callback(
    code: str,
    state: str,  # This will contain the slack_user_id
    slack_auth_service: SlackAuthService = Depends(get_slack_auth_service)
):
    """Handle Google Drive authentication callback"""
    try:
        success = slack_auth_service.handle_auth_callback(code, state)
        if success:
            return RedirectResponse(url="https://slack.com/app_redirect?app=YOUR_APP_ID")
        else:
            raise HTTPException(status_code=400, detail="Authentication failed")
    except Exception as e:
        logger.error(f"Error handling auth callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 