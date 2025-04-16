from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from ..core.config import settings
from .chat_service import ChatService
from ..db.models import SlackUser
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SlackService:
    def __init__(self, chat_service: ChatService, db: Session):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.chat_service = chat_service
        self.db = db
        
    async def is_user_authenticated(self, user_id: str) -> bool:
        """Check if a user is authenticated with Google Drive"""
        user = self.db.query(SlackUser).filter(SlackUser.slack_user_id == user_id).first()
        return user is not None and user.google_drive_token is not None
        
    async def store_google_tokens(self, user_id: str, access_token: str, refresh_token: str, expires_in: int) -> None:
        """Store Google Drive tokens for a Slack user"""
        try:
            user = self.db.query(SlackUser).filter(SlackUser.slack_user_id == user_id).first()
            if not user:
                user = SlackUser(slack_user_id=user_id)
                self.db.add(user)
            
            user.google_drive_token = access_token
            user.google_drive_refresh_token = refresh_token
            user.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            self.db.commit()
            logger.info(f"Stored Google Drive tokens for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing Google Drive tokens: {str(e)}")
            self.db.rollback()
            raise
            
    async def get_google_tokens(self, user_id: str) -> dict:
        """Retrieve Google Drive tokens for a Slack user"""
        try:
            user = self.db.query(SlackUser).filter(SlackUser.slack_user_id == user_id).first()
            if not user or not user.google_drive_token:
                return None
                
            # Check if token is expired
            if user.token_expires_at and user.token_expires_at <= datetime.utcnow():
                # Token is expired, we'll need to refresh it
                return {
                    "access_token": user.google_drive_token,
                    "refresh_token": user.google_drive_refresh_token,
                    "expires_at": user.token_expires_at,
                    "needs_refresh": True
                }
                
            return {
                "access_token": user.google_drive_token,
                "refresh_token": user.google_drive_refresh_token,
                "expires_at": user.token_expires_at,
                "needs_refresh": False
            }
        except Exception as e:
            logger.error(f"Error retrieving Google Drive tokens: {str(e)}")
            return None
            
    async def clear_google_tokens(self, user_id: str) -> None:
        """Clear Google Drive tokens for a Slack user"""
        try:
            user = self.db.query(SlackUser).filter(SlackUser.slack_user_id == user_id).first()
            if user:
                user.google_drive_token = None
                user.google_drive_refresh_token = None
                user.token_expires_at = None
                self.db.commit()
                logger.info(f"Cleared Google Drive tokens for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing Google Drive tokens: {str(e)}")
            self.db.rollback()
            raise
        
    async def handle_mention(self, event_data: dict) -> None:
        """Handle app mention events"""
        try:
            # Extract channel and text from the event
            channel_id = event_data.get("channel")
            text = event_data.get("text", "")
            user = event_data.get("user")
            
            # Remove the bot mention from the text
            # Format is typically <@BOT_ID> command
            command = " ".join(text.split()[1:]) if text else ""
            
            logger.debug(f"Processing command from mention: {command}")
            
            if not command:
                await self.send_message(channel_id, "How can I help you? Try typing 'help' to see available commands.")
                return
                
            # Process the command through our chat service
            response = await self.chat_service.process_message(command)
            
            # Send the response back to Slack
            await self.send_message(channel_id, response.get("content", "Sorry, I couldn't process that command."))
            
        except Exception as e:
            logger.error(f"Error handling mention: {str(e)}", exc_info=True)
            await self.send_message(channel_id, f"Sorry, I encountered an error processing your request: {str(e)}")
    
    async def handle_slash_command(self, command_data: dict) -> dict:
        """Handle slash commands"""
        try:
            logger.debug(f"Received command data: {command_data}")
            
            # Extract command text and channel
            command_text = command_data.get("text", "")
            channel_id = command_data.get("channel_id")
            user_id = command_data.get("user_id")
            
            logger.debug(f"Processing slash command: {command_text} from user {user_id} in channel {channel_id}")
            
            if not command_text:
                return {
                    "response_type": "ephemeral",
                    "text": "Please provide a command. Try 'help' to see available commands."
                }
            
            # Check if this is an auth command
            if command_text.strip().lower() == "auth":
                if not user_id:
                    return {
                        "response_type": "ephemeral",
                        "text": "Could not determine your Slack user ID. Please try again."
                    }
                
                # Check if user already exists
                user = self.db.query(SlackUser).filter(SlackUser.slack_user_id == user_id).first()
                if not user:
                    user = SlackUser(slack_user_id=user_id)
                    self.db.add(user)
                    self.db.commit()
                
                # Send a direct message to the user
                try:
                    # Open a DM channel with the user
                    dm_channel = await self.client.conversations_open(users=user_id)
                    channel_id = dm_channel["channel"]["id"]
                    
                    # Send the auth message with a proper OAuth URL
                    auth_url = f"{settings.API_BASE_URL}/api/v1/slack/auth/url?slack_user_id={user_id}"
                    await self.send_message(
                        channel_id,
                        f"Please authenticate with Google Drive by visiting this URL: {auth_url}"
                    )
                    
                    return {
                        "response_type": "ephemeral",
                        "text": "I've sent you an authentication link. Please check your direct messages."
                    }
                except Exception as e:
                    logger.error(f"Error sending DM: {str(e)}")
                    return {
                        "response_type": "ephemeral",
                        "text": "I couldn't send you a direct message. Please make sure you've allowed the app to send you messages."
                    }
            
            # Allow help command without authentication
            if command_text.strip().lower() == "help":
                help_text = """
Available commands:
• `/testlegacy help` - Show this help message
• `/testlegacy auth` - Authenticate with Google Drive
• `/testlegacy list` - List recent files from your drive
• `/testlegacy inactive` - Show files that haven't been modified in the last 12 months
• `/testlegacy find` - Search for a specific file (e.g., find report.pdf)
• `/testlegacy status` - Check your authentication status
• `/testlegacy directories` - List your top-level folders
• `/testlegacy categorize` - Show a summary of a folder's contents
                """
                return {
                    "response_type": "ephemeral",
                    "text": help_text
                }
            
            # Check if the user is authenticated for other commands
            if not await self.is_user_authenticated(user_id):
                logger.debug("User is not authenticated with Google Drive")
                return {
                    "response_type": "ephemeral",
                    "text": "Please authenticate first using `/testlegacy auth`"
                }
            
            # Process other commands
            logger.debug(f"Sending command to chat service: {command_text}")
            response = await self.chat_service.process_message(command_text)
            logger.debug(f"Received response from chat service: {response}")
            
            # Send the response to the channel
            await self.send_message(channel_id, response.get("content", "Sorry, I couldn't process that command."))
            
            return {
                "response_type": "in_channel",
                "text": "Command processed successfully!"
            }
            
        except Exception as e:
            logger.error(f"Error handling slash command: {str(e)}", exc_info=True)
            return {
                "response_type": "ephemeral",
                "text": f"Sorry, I encountered an error processing your command: {str(e)}"
            }
    
    async def send_message(self, channel: str, text: str) -> None:
        """Send a message to a Slack channel"""
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text
            )
            logger.debug(f"Message sent to channel {channel}")
        except SlackApiError as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=True) 