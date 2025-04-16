from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ....services.chat_service import ChatService
from ....services.google_drive import GoogleDriveService
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter()

# Create a single instance of GoogleDriveService
drive_service = GoogleDriveService()
chat_service = ChatService(drive_service)

class ChatMessage(BaseModel):
    message: str

@router.post("/messages")
async def process_message(chat_message: ChatMessage):
    """Process a chat message and return a response."""
    try:
        response = await chat_service.process_message(chat_message.message)
        return response
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/command")
async def handle_command(command: dict):
    """Handle chat commands."""
    try:
        logger.info(f"Received command: {command}")
        
        # Check authentication status
        auth_status = drive_service.is_authenticated()
        logger.info(f"Authentication status: {auth_status}")
        
        if not auth_status:
            return {
                "type": "error",
                "message": "Not authenticated with Google Drive. Please authenticate first."
            }
        
        # Get the command string
        cmd = command.get("command", "")
        logger.info(f"Processing command: {cmd}")
        
        # Process the command
        response = await chat_service.process_command(cmd)
        logger.info(f"Command response: {response}")
        
        return response
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e)) 