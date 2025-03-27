from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ....services.chat_service import ChatService
from .drive import drive_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
chat_service = ChatService(drive_service)

class ChatMessage(BaseModel):
    message: str

@router.post("/message")
async def process_message(chat_message: ChatMessage):
    """Process a chat message and return a response."""
    try:
        response = await chat_service.process_message(chat_message.message)
        return response
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 