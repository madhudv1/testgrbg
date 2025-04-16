from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class SlackUser(Base):
    __tablename__ = "slack_users"
    
    id = Column(Integer, primary_key=True, index=True)
    slack_user_id = Column(String, unique=True, index=True)
    email = Column(String)
    google_drive_token = Column(String)
    google_drive_refresh_token = Column(String)
    token_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 