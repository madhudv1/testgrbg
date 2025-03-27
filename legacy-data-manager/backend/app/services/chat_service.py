from typing import Dict, List, Optional
from .google_drive import GoogleDriveService
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, drive_service: GoogleDriveService):
        self.drive_service = drive_service
        self.commands = {
            "help": self._handle_help,
            "list": self._handle_list,
            "inactive": self._handle_inactive,
            "find": self._handle_find,
            "status": self._handle_status
        }

    async def process_message(self, message: str) -> Dict:
        """Process a user message and return a response."""
        message = message.lower().strip()
        
        # Check if it's a command
        for cmd, handler in self.commands.items():
            if message.startswith(cmd):
                return await handler(message[len(cmd):].strip())
        
        # Default response for unknown commands
        return {
            "type": "text",
            "content": "I'm not sure how to help with that. Type 'help' to see what I can do!"
        }

    async def _handle_help(self, _: str) -> Dict:
        """Handle the help command."""
        return {
            "type": "text",
            "content": """I can help you with the following commands:
- help: Show this help message
- list: List recent files
- inactive: Show inactive files
- find <filename>: Search for a specific file
- status: Check authentication status

Try any of these commands!"""
        }

    async def _handle_list(self, _: str) -> Dict:
        """Handle the list command."""
        if not self.drive_service.is_authenticated():
            return {
                "type": "text",
                "content": "Please authenticate first using the /auth/url endpoint"
            }
        
        try:
            files = self.drive_service.list_files(page_size=5)
            if not files:
                return {
                    "type": "text",
                    "content": "No files found in your drive."
                }
            
            response = "Here are your recent files:\n"
            for file in files:
                response += f"- {file['name']} (Last modified: {file['modifiedTime']})\n"
            
            return {
                "type": "text",
                "content": response
            }
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return {
                "type": "text",
                "content": f"Sorry, I encountered an error: {str(e)}"
            }

    async def _handle_inactive(self, _: str) -> Dict:
        """Handle the inactive command."""
        if not self.drive_service.is_authenticated():
            return {
                "type": "text",
                "content": "Please authenticate first using the /auth/url endpoint"
            }
        
        try:
            files = self.drive_service.get_inactive_files()
            if not files:
                return {
                    "type": "text",
                    "content": "No inactive files found."
                }
            
            response = "Here are your inactive files:\n"
            for file in files:
                response += f"- {file['name']} (Last modified: {file['modifiedTime']})\n"
            
            return {
                "type": "text",
                "content": response
            }
        except Exception as e:
            logger.error(f"Error listing inactive files: {str(e)}")
            return {
                "type": "text",
                "content": f"Sorry, I encountered an error: {str(e)}"
            }

    async def _handle_find(self, query: str) -> Dict:
        """Handle the find command."""
        if not query:
            return {
                "type": "text",
                "content": "Please provide a search term. Example: find report.pdf"
            }
        
        if not self.drive_service.is_authenticated():
            return {
                "type": "text",
                "content": "Please authenticate first using the /auth/url endpoint"
            }
        
        try:
            files = self.drive_service.list_files(page_size=10)
            matching_files = [
                file for file in files 
                if query.lower() in file['name'].lower()
            ]
            
            if not matching_files:
                return {
                    "type": "text",
                    "content": f"No files found matching '{query}'"
                }
            
            response = f"Found {len(matching_files)} matching files:\n"
            for file in matching_files:
                response += f"- {file['name']} (Last modified: {file['modifiedTime']})\n"
            
            return {
                "type": "text",
                "content": response
            }
        except Exception as e:
            logger.error(f"Error searching files: {str(e)}")
            return {
                "type": "text",
                "content": f"Sorry, I encountered an error: {str(e)}"
            }

    async def _handle_status(self, _: str) -> Dict:
        """Handle the status command."""
        is_authenticated = self.drive_service.is_authenticated()
        return {
            "type": "text",
            "content": "Authenticated" if is_authenticated else "Not authenticated. Please authenticate first using the /auth/url endpoint"
        } 