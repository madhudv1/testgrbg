from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
import googleapiclient.discovery
import uuid # For generating state for Klio
import json # For encoding state
import logging

from ....core.config import settings
from ....db.database import get_db
from ....services.slack_service import SlackService # Assuming SlackService handles token storage

router = APIRouter()

# Define Google OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly'] # Add more scopes if needed

def get_google_flow() -> Flow:
    """Initializes the Google OAuth flow."""
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

# Dependency to get SlackService (assuming it's set up for dependency injection)
# You might need to adjust this based on your actual dependency setup in main.py
def get_slack_service(db: Session = Depends(get_db)) -> SlackService:
    # This assumes ChatService dependency is handled elsewhere or not needed for token storage
    # If ChatService is required by SlackService init, you need to inject it here too.
    # For now, let's assume a simpler SlackService or adjust later.
    # Placeholder: You might need to fetch ChatService properly.
    from ....services.chat_service import ChatService # Temporary import, fix dependency injection later
    chat_service = ChatService(db=db) # Placeholder instantiation
    return SlackService(chat_service=chat_service, db=db)


@router.get("/google/login", summary="Initiate Google OAuth2 flow for Slack or Klio")
async def google_login(request: Request, origin: str = Query(...), slack_user_id: str = Query(None)):
    """
    Redirects the user to Google's consent screen.
    Requires 'origin' (e.g., 'slack', 'klio').
    If origin is 'slack', requires 'slack_user_id'.
    """
    flow = get_google_flow()
    
    state_data = {"origin": origin}
    if origin == "slack":
        if not slack_user_id:
            raise HTTPException(status_code=400, detail="slack_user_id is required for origin 'slack'")
        state_data["slack_user_id"] = slack_user_id
    elif origin == "klio":
        # For Klio, generate a unique ID to track the session temporarily
        # In a real app, use proper session management (e.g., FastAPI sessions)
        session_id = str(uuid.uuid4())
        state_data["session_id"] = session_id
        # TODO: Store session_id temporarily if needed for validation later
    else:
        raise HTTPException(status_code=400, detail="Invalid origin specified")

    # Encode state data as JSON string
    encoded_state = json.dumps(state_data)

    authorization_url, state = flow.authorization_url(
        access_type='offline', 
        prompt='consent',
        state=encoded_state
    )
        
    return RedirectResponse(authorization_url)


@router.get("/google/callback", summary="Handle Google OAuth2 callback")
async def google_callback(
    request: Request, 
    code: str = Query(...), 
    state: str = Query(...),
    db: Session = Depends(get_db),
    slack_service: SlackService = Depends(get_slack_service) 
):
    """
    Handles the callback from Google, exchanges code for tokens.
    Stores tokens for Slack users, redirects Klio users.
    """
    try:
        state_data = json.loads(state)
        origin = state_data.get("origin")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid state parameter format")

    try:
        flow = get_google_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Validate that we have a refresh token
        if not credentials.refresh_token:
            logger.error("No refresh token received from Google OAuth flow")
            if origin == "klio":
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/?auth=error&message=No refresh token received. Please revoke access and try again.")
            else:
                raise HTTPException(status_code=400, detail="No refresh token received")
        
        if origin == "slack":
            slack_user_id = state_data.get("slack_user_id")
            if not slack_user_id:
                raise HTTPException(status_code=400, detail="Missing slack_user_id in state for Slack origin")
            await slack_service.store_google_tokens(
                user_id=slack_user_id,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                expires_in=credentials.expires_in 
            )
            return JSONResponse(content={"message": f"Successfully authenticated Google Drive for Slack user {slack_user_id}."})
        
        elif origin == "klio":
            # Store credentials in token file
            with open('token.pickle', 'wb') as token:
                import pickle
                pickle.dump(credentials, token)
            
            # Redirect to frontend with success status
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/?auth=success")
            
        else:
            raise HTTPException(status_code=400, detail="Invalid origin in state")

    except Exception as e:
        logger.error(f"Error during Google OAuth callback: {e}")
        if origin == "klio":
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/?auth=error&message={str(e)}")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to authenticate with Google: {str(e)}")


@router.get("/google/status", summary="Check Google Auth status (basic implementation)")
async def google_status(request: Request, slack_user_id: str = Query(None), db: Session = Depends(get_db)):
    """
    Checks if a user is authenticated with Google.
    If slack_user_id is provided, checks DB for that user.
    Otherwise (for Klio), returns a basic status (e.g., based on session - NOT IMPLEMENTED YET).
    """
    if slack_user_id:
        slack_service = get_slack_service(db=db)
        is_authenticated = await slack_service.is_user_authenticated(slack_user_id)
        return {"isAuthenticated": is_authenticated, "userType": "slack"}
    else:
        # Klio status check - VERY BASIC PLACEHOLDER
        # In a real app, check session data for stored tokens/auth status
        # For now, assume not authenticated until callback succeeds and potentially sets a session flag
        # (which we haven't implemented yet)
        print("Klio auth status check: Session/Token check not implemented yet.")
        return {"isAuthenticated": False, "userType": "klio", "detail": "Web user status check not fully implemented"}

# Add /status endpoint later if needed 