from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# User schemas
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    role: str = "member"
    credits: int = 100

class UserResponse(UserBase):
    id: int
    role: str
    credits: int
    api_key: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Rule schemas
class RuleBase(BaseModel):
    pattern: str
    action: str
    description: Optional[str] = None
    priority: int = 0

class RuleCreate(RuleBase):
    pass

class RuleResponse(RuleBase):
    id: int
    created_by: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

# Command schemas
class CommandBase(BaseModel):
    command_text: str

class CommandCreate(CommandBase):
    pass

class CommandResponse(CommandBase):
    id: int
    user_id: int
    status: str
    matched_rule_id: Optional[int]
    executed_at: Optional[datetime]
    result: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Audit log schemas
class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Credit schemas
class CreditResponse(BaseModel):
    credits: int

# Execution schemas
class ExecutionResult(BaseModel):
    success: bool
    message: str
    credits_used: int = 0
    remaining_credits: int = 0