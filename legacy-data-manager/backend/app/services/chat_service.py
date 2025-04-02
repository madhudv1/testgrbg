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
            "status": self._handle_status,
            "directories": self._handle_directories,
            "categorize": self._handle_categorize
        }

    async def process_message(self, message: str) -> Dict:
        """Process a user message and return a response."""
        original_message = message.strip()
        lower_message = original_message.lower() # Lowercase version for command matching
        
        # Check if it's a command
        for cmd, handler in self.commands.items():
            # Match against the lowercase version
            if lower_message.startswith(cmd):
                # Extract arguments from the *original* message to preserve case
                # Add a space check to handle commands with and without args correctly
                if len(original_message) > len(cmd) and original_message[len(cmd)] == ' ':
                    arguments = original_message[len(cmd):].strip()
                elif len(original_message) == len(cmd):
                     arguments = "" # Command was entered with no arguments
                else:
                    # Command doesn't match exactly (e.g., typed 'listx' when command is 'list')
                    # This case might not be strictly needed if startswith is sufficient,
                    # but added for robustness. Let default handle it.
                    continue 
                    
                return await handler(arguments) # Pass original-case arguments
        
        # Default response for unknown commands or commands needing arguments but not provided
        logger.warning(f"Unknown command or format: {original_message}")
        return {
            "type": "text",
            "content": "I'm not sure how to help with that, or the command format was incorrect. Type 'help' to see available commands and formats."
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
- directories: List your top-level folders
- categorize <folder_id>: Show a summary of a folder's contents

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

    async def _handle_directories(self, _: str) -> Dict:
        """Handle the directories command."""
        if not self.drive_service.is_authenticated():
            return {
                "type": "text",
                "content": "Please authenticate first using the /auth/url endpoint"
            }
        
        try:
            directories = self.drive_service.list_directories(page_size=100)
            if not directories:
                return {
                    "type": "text",
                    "content": "No top-level directories found that you own."
                }
            
            response = "Here are your top-level directories:\n"
            for directory in directories:
                response += f"- {directory['name']} (ID: {directory['id']})\n"
            
            return {
                "type": "text",
                "content": response
            }
        except Exception as e:
            logger.error(f"Error listing directories: {str(e)}")
            return {
                "type": "text",
                "content": f"Sorry, I encountered an error listing directories: {str(e)}"
            }

    async def _handle_categorize(self, folder_id: str) -> Dict:
        """Handle the categorize command."""
        if not folder_id:
            return {
                "type": "text",
                "content": "Please provide a folder ID. Example: categorize 1A2B3C..."
            }
            
        if not self.drive_service.is_authenticated():
            return {
                "type": "text",
                "content": "Please authenticate first using the /auth/url endpoint"
            }
            
        try:
            categories = self.drive_service.categorize_directory(folder_id)
            summary = categories.get('summary', {})
            
            if not summary or summary.get('total_files', 0) == 0:
                 return {
                    "type": "text",
                    "content": f"Could not find or categorize folder with ID '{folder_id}'. It might be empty or inaccessible."
                }

            response = f"Summary for folder ID {folder_id}:\n"
            response += f"- Total Files: {summary.get('total_files', 0)}\n"
            response += f"- Total Size: {summary.get('total_size', 0)} bytes\n"
            response += "- Files by Type:\n"
            for type_name, count in summary.get('by_type', {}).items():
                if count > 0:
                    response += f"    - {type_name.capitalize()}: {count}\n"
            response += f"- Recent Files (last 30 days): {summary.get('recent_files', 0)}\n"
            response += f"- Large Files (>10MB): {summary.get('large_files', 0)}\n"
            response += f"- Number of Owners: {summary.get('owners', 0)}\n"
            
            return {
                "type": "text",
                "content": response
            }
        except Exception as e:
            logger.error(f"Error categorizing directory {folder_id}: {str(e)}", exc_info=True)
            return {
                "type": "text",
                "content": f"Sorry, I encountered an error categorizing the directory: {str(e)}"
            } 