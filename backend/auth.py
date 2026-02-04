# backend/auth.py
# API key authentication & role checks

from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, AuditLog
from typing import Optional

async def get_current_user(
    x_api_key: str = Header(..., description="API Key for authentication"),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from API key.
    Raises 401 if API key is invalid.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    user = db.query(User).filter(User.api_key == x_api_key).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure the current user is an admin.
    Raises 403 if user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


def log_audit(
    db: Session,
    user: Optional[User],
    action: str,
    command_text: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None
):
    """
    Create an audit log entry.
    """
    audit_log = AuditLog(
        user_id=user.id if user else None,
        action=action,
        command_text=command_text,
        details=details,
        ip_address=ip_address
    )
    db.add(audit_log)
    # Note: Commit is handled by the calling function for transaction support
    return audit_log


def verify_credits(user: User, required_credits: int = 1) -> bool:
    """
    Check if user has sufficient credits.
    """
    return user.credits >= required_credits


def deduct_credits(db: Session, user: User, amount: int = 1) -> bool:
    """
    Deduct credits from user account.
    Returns True if successful, False if insufficient credits.
    """
    if user.credits < amount:
        return False
    
    user.credits -= amount
    db.add(user)
    return True
