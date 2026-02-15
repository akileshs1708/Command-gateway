# backend/models.py
# DB models: User, Rule, Command, AuditLog

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import secrets
import string

class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    role = Column(String(20), nullable=False, default="member")  # 'admin' or 'member'
    credits = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    commands = relationship("Command", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    @staticmethod
    def generate_api_key():
        """Generate a secure random API key."""
        alphabet = string.ascii_letters + string.digits
        return 'key-' + ''.join(secrets.choice(alphabet) for _ in range(32))
    
    def to_dict(self, include_api_key=False):
        """Convert to dictionary for API responses."""
        data = {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "credits": self.credits,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if include_api_key:
            data["api_key"] = self.api_key
        return data


class Rule(Base):
    """Rule model for command pattern matching."""
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern = Column(String(255), nullable=False)
    action = Column(String(20), nullable=False)  # 'AUTO_ACCEPT' or 'AUTO_REJECT'
    priority = Column(Integer, nullable=False, default=10)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "action": self.action,
            "priority": self.priority,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Command(Base):
    """Command model for tracking submitted commands."""
    __tablename__ = "commands"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    command_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)  # 'accepted', 'rejected', 'executed'
    matched_rule_id = Column(Integer, ForeignKey("rules.id"), nullable=True)
    matched_pattern = Column(String(255), nullable=True)
    credits_deducted = Column(Integer, nullable=False, default=0)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="commands")
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "command_text": self.command_text,
            "status": self.status,
            "matched_pattern": self.matched_pattern,
            "credits_deducted": self.credits_deducted,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(Base):
    """Audit log model for tracking all system actions."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    command_text = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "action": self.action,
            "command_text": self.command_text,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
