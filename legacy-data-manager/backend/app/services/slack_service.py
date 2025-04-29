from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from ..core.config import settings
from .chat_service import ChatService
from ..db.models import SlackUser
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SlackMessageTemplates:
    @staticmethod
    def status_message(health_score: int, urgent_items: List[str], dashboard_url: str) -> Dict:
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Drive Health Status 🏥"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Health Score:* {health_score}/100"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Urgent Items:*\n" + 
                            "\n".join(f"• {item}" for item in urgent_items)}
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Details"},
                            "url": dashboard_url
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def analyze_message(directory: str, summary: Dict[str, Any], dashboard_url: str) -> Dict:
        """Create a detailed analysis message for Slack."""
        # Create the header
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Analysis Results: {directory} 📊"}
            }
        ]
        
        # Add cache status if applicable
        if summary.get('is_cached'):
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "ℹ️ Showing cached results from previous analysis"
                    }
                ]
            })
        
        # Add basic statistics
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": 
                f"*Basic Statistics:*\n" +
                f"• Total Files: {summary['total_files']}\n" +
                f"• Sensitive Files: {summary['sensitive_files']}\n" +
                f"• Old Files (>3y): {summary['old_files']}\n" +
                f"• Storage Used: {summary['storage_used']}%"
            }
        })
        
        # Add file type distribution
        if summary.get('file_types'):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": 
                    "*File Type Distribution:*\n" +
                    "\n".join(f"• {file_type}: {count}" for file_type, count in summary['file_types'].items() if count > 0)
                }
            })
        
        # Add age distribution
        if summary.get('age_distribution'):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": 
                    "*Age Distribution:*\n" +
                    "\n".join(f"• {age}: {count}" for age, count in summary['age_distribution'].items() if count > 0)
                }
            })
        
        # Add risk assessment
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": 
                f"*Risk Assessment:*\n" +
                f"• Risk Level: {summary['risk_level']}\n" +
                f"• Risk Score: {summary['risk_score']}/100"
            }
        })
        
        # Add key findings
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": 
                "*Key Findings:*\n" + 
                "\n".join(f"• {finding}" for finding in summary['key_findings'])
            }
        })
        
        # Add action button
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Detailed Analysis"},
                    "url": dashboard_url
                }
            ]
        })
        
        return {"blocks": blocks}

    @staticmethod
    def summary_message(stats: Dict[str, Any], dashboard_url: str) -> Dict:
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Drive Summary 📈"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": 
                        f"*Total Files:* {stats['total_files']}\n" +
                        f"*Storage Used:* {stats['storage_used_percentage']}%\n" +
                        f"*Sensitive Files:* {stats['sensitive_files']}\n" +
                        f"*Old Files:* {stats['old_files']}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Open Dashboard"},
                            "url": dashboard_url
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def help_message() -> Dict:
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Available Commands 🤖"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": 
                        "*Basic Commands:*\n" +
                        "• `/testlegacy help` - Show this help message\n" +
                        "• `/testlegacy status` - Show drive health status\n" +
                        "• `/testlegacy list` - List directories\n\n" +
                        "*Analysis Commands:*\n" +
                        "• `/testlegacy analyze [dir]` - Analyze a directory\n" +
                        "• `/testlegacy summary [dir]` - Show directory summary\n" +
                        "• `/testlegacy risks [dir]` - Show risk analysis"
                    }
                }
            ]
        }

class SlackService:
    def __init__(self, chat_service: ChatService, db: Session):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.chat_service = chat_service
        self.db = db
        self.templates = SlackMessageTemplates()
        self.dashboard_base_url = settings.FRONTEND_URL
        
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
            
            command_text = command_data.get("text", "").strip()
            channel_id = command_data.get("channel_id")
            user_id = command_data.get("user_id")
            
            if not command_text:
                return self.templates.help_message()

            # Parse command and arguments
            parts = command_text.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            # Command handlers
            handlers = {
                "help": self._handle_help,
                "status": self._handle_status,
                "analyze": self._handle_analyze,
                "summary": self._handle_summary,
                "list": self._handle_list,
                "risks": self._handle_risks
            }

            handler = handlers.get(command)
            if not handler:
                return {
                    "response_type": "ephemeral",
                    "text": f"Unknown command: {command}. Try `/testlegacy help` for available commands."
                }

            return await handler(args, user_id, channel_id)

        except Exception as e:
            logger.error(f"Error handling slash command: {str(e)}", exc_info=True)
            return {
                "response_type": "ephemeral",
                "text": f"Sorry, I encountered an error processing your command: {str(e)}"
            }

    async def _handle_help(self, args: List[str], user_id: str, channel_id: str) -> Dict:
        return self.templates.help_message()

    async def _handle_status(self, args: List[str], user_id: str, channel_id: str) -> Dict:
        try:
            # Get drive statistics from chat service
            stats = await self.chat_service.get_drive_stats()
            
            # Calculate health score (implement this logic)
            health_score = self._calculate_health_score(stats)
            
            # Determine urgent items
            urgent_items = self._get_urgent_items(stats)
            
            # Just point to the main dashboard
            dashboard_url = f"{self.dashboard_base_url}"
            
            return self.templates.status_message(health_score, urgent_items, dashboard_url)
        except Exception as e:
            logger.error(f"Error in status command: {str(e)}", exc_info=True)
            return {"response_type": "ephemeral", "text": f"Error getting status: {str(e)}"}

    async def _handle_analyze(self, args: List[str], user_id: str, channel_id: str) -> Dict:
        if not args:
            return {
                "response_type": "ephemeral",
                "text": "Please specify a directory to analyze. Usage: `/testlegacy analyze [directory]`"
            }

        directory = " ".join(args)
        try:
            # Start analysis in chat service
            analysis_results = await self.chat_service.analyze_directory(directory)
            
            # Create summary from results
            summary = self._create_analysis_summary(analysis_results)
            
            # Just point to the main dashboard
            dashboard_url = f"{self.dashboard_base_url}"
            
            return self.templates.analyze_message(directory, summary, dashboard_url)
        except ValueError as e:
            logger.error(f"Value error in analyze command: {str(e)}")
            return {
                "response_type": "ephemeral",
                "text": f"Error: {str(e)}\nPlease make sure the directory ID is valid and you have access to it."
            }
        except Exception as e:
            error_msg = str(e)
            if "File not found" in error_msg or "notFound" in error_msg:
                logger.error(f"Directory not found error: {error_msg}")
                return {
                    "response_type": "ephemeral",
                    "text": f"Error: Directory not found. Please check if the directory ID '{directory}' is correct and you have access to it."
                }
            else:
                logger.error(f"Error in analyze command: {error_msg}", exc_info=True)
                return {
                    "response_type": "ephemeral",
                    "text": f"An error occurred while analyzing the directory. Please try again later or contact support if the issue persists."
                }

    async def _handle_summary(self, args: List[str], user_id: str, channel_id: str) -> Dict:
        try:
            # Get directory from args if provided
            directory = " ".join(args) if args else None
            
            # Get summary statistics
            stats = await self.chat_service.get_summary_stats(directory)
            
            # Just point to the main dashboard
            dashboard_url = f"{self.dashboard_base_url}"
            
            return self.templates.summary_message(stats, dashboard_url)
        except Exception as e:
            logger.error(f"Error in summary command: {str(e)}", exc_info=True)
            return {"response_type": "ephemeral", "text": f"Error getting summary: {str(e)}"}

    async def _handle_list(self, args: List[str], user_id: str, channel_id: str) -> Dict:
        try:
            # Use the chat service's list handler
            response = await self.chat_service._handle_list("")
            
            # Convert the response to Slack format
            return {
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "Available Directories 📁"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": response["content"]}
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error in list command: {str(e)}", exc_info=True)
            return {"response_type": "ephemeral", "text": f"Error listing directories: {str(e)}"}

    async def _handle_risks(self, args: List[str], user_id: str, channel_id: str) -> Dict:
        if not args:
            return {
                "response_type": "ephemeral",
                "text": "Please specify a directory. Usage: `/testlegacy risks [directory]`"
            }

        directory = " ".join(args)
        try:
            # Get risk analysis
            risks = await self.chat_service.analyze_risks(directory)
            
            # Just point to the main dashboard
            dashboard_url = f"{self.dashboard_base_url}"
            
            return {
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"Risk Analysis: {directory} 🚨"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": self._format_risks(risks)}
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Details"},
                                "url": dashboard_url
                            }
                        ]
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error in risks command: {str(e)}", exc_info=True)
            return {"response_type": "ephemeral", "text": f"Error analyzing risks: {str(e)}"}

    def _calculate_health_score(self, stats: Dict[str, Any]) -> int:
        # Implement health score calculation logic
        # This is a placeholder implementation
        base_score = 100
        deductions = 0
        
        # Deduct for sensitive files
        sensitive_files = stats.get('sensitive_files', 0)
        deductions += min(sensitive_files * 2, 30)
        
        # Deduct for old files
        old_files = stats.get('old_files', 0)
        deductions += min(old_files, 20)
        
        # Deduct for storage usage
        storage_used = stats.get('storage_used_percentage', 0)
        if storage_used > 80:
            deductions += 10
        elif storage_used > 60:
            deductions += 5
        
        return max(base_score - deductions, 0)

    def _get_urgent_items(self, stats: Dict[str, Any]) -> List[str]:
        urgent_items = []
        
        sensitive_files = stats.get('sensitive_files', 0)
        if sensitive_files > 0:
            urgent_items.append(f"🔒 {sensitive_files} sensitive files need review")
            
        old_files = stats.get('old_files', 0)
        if old_files > 0:
            urgent_items.append(f"📅 {old_files} files are over 3 years old")
            
        storage_used = stats.get('storage_used_percentage', 0)
        if storage_used > 80:
            urgent_items.append(f"💾 Storage usage is at {storage_used}%")
            
        return urgent_items

    def _create_analysis_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a detailed summary from analysis results."""
        # Basic statistics
        total_files = results.get('total_files', 0)
        sensitive_files = results.get('sensitive_files', 0)
        old_files = results.get('old_files', 0)
        storage_used = results.get('storage_used', 0)
        
        # File type distribution
        file_types = results.get('file_types', {})
        file_type_summary = []
        for file_type, count in file_types.items():
            if count > 0:
                percentage = (count / total_files * 100) if total_files > 0 else 0
                file_type_summary.append(f"{file_type}: {count} ({percentage:.1f}%)")
        
        # Age distribution
        age_distribution = results.get('age_distribution', {})
        age_summary = []
        for age, count in age_distribution.items():
            if count > 0:
                percentage = (count / total_files * 100) if total_files > 0 else 0
                age_summary.append(f"{age}: {count} ({percentage:.1f}%)")
        
        # Risk assessment
        risk_level = results.get('risk_level', 'Unknown')
        risk_score = results.get('risk_score', 0)
        
        # Key findings
        key_findings = []
        if sensitive_files > 0:
            key_findings.append(f"🔒 Found {sensitive_files} sensitive files")
        if old_files > 0:
            key_findings.append(f"📅 {old_files} files are over 3 years old")
        if storage_used > 80:
            key_findings.append(f"⚠️ High storage usage: {storage_used}%")
        elif storage_used > 60:
            key_findings.append(f"📊 Moderate storage usage: {storage_used}%")
        
        # Add file type insights
        if file_type_summary:
            key_findings.append(f"📁 File types: {', '.join(file_type_summary)}")
        
        # Add age distribution insights
        if age_summary:
            key_findings.append(f"⏳ Age distribution: {', '.join(age_summary)}")
        
        # Add risk assessment
        key_findings.append(f"🚨 Risk level: {risk_level} (Score: {risk_score}/100)")
        
        return {
            'total_files': total_files,
            'sensitive_files': sensitive_files,
            'old_files': old_files,
            'storage_used': storage_used,
            'file_types': file_types,
            'age_distribution': age_distribution,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'key_findings': key_findings,
            'is_cached': results.get('is_cached', False)
        }

    def _format_risks(self, risks: Dict[str, Any]) -> str:
        return (
            f"*Risk Summary:*\n" +
            f"• Sensitive Files: {risks.get('sensitive_files', 0)}\n" +
            f"• High Risk: {risks.get('high_risk', 0)}\n" +
            f"• Medium Risk: {risks.get('medium_risk', 0)}\n" +
            f"• Low Risk: {risks.get('low_risk', 0)}\n\n" +
            "*Top Concerns:*\n" +
            "\n".join(f"• {concern}" for concern in risks.get('top_concerns', []))
        )

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