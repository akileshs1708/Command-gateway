from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import uvicorn

from database import get_db, init_db, engine, Base
from models import User, Rule, Command, AuditLog
from auth import get_current_user, get_current_admin, log_audit
from rules import (
    match_command, create_rule, delete_rule, 
    get_sorted_rules, get_default_rules, validate_regex_pattern
)
from commands import submit_command, get_user_commands, get_all_commands

# Create FastAPI app
app = FastAPI(
    title="Command Gateway API",
    description="Secure command execution gateway with role-based access control",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Pydantic Models ====================

class CommandSubmit(BaseModel):
    command: str = Field(..., min_length=1, max_length=1000)

class RuleCreate(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=255)
    action: str = Field(..., pattern="^(AUTO_ACCEPT|AUTO_REJECT)$")
    priority: int = Field(default=10, ge=1, le=1000)
    description: Optional[str] = Field(default=None, max_length=255)

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    role: str = Field(default="member", pattern="^(admin|member)$")
    credits: int = Field(default=100, ge=0, le=10000)

class CreditAdjust(BaseModel):
    credits: int = Field(..., ge=0, le=100000)

class MessageResponse(BaseModel):
    message: str

class CreditsResponse(BaseModel):
    credits: int
    username: str


# ==================== Startup Events ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database and seed default data."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = next(get_db())
    try:
        # Check if admin user exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            # Create default admin user
            admin = User(
                username="admin",
                api_key="admin-key-12345",
                role="admin",
                credits=1000
            )
            db.add(admin)
            print("Created default admin user (API key: admin-key-12345)")
        
        # Check if rules exist
        rule_count = db.query(Rule).count()
        if rule_count == 0:
            # Seed default rules
            for rule_data in get_default_rules():
                rule = Rule(**rule_data)
                db.add(rule)
            print(f"Seeded {len(get_default_rules())} default rules")
        
        db.commit()
    except Exception as e:
        print(f"Startup error: {e}")
        db.rollback()
    finally:
        db.close()


# ==================== Member Endpoints ====================

@app.post("/commands", tags=["Commands"])
async def submit_command_endpoint(
    cmd: CommandSubmit,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a command for execution.
    
    The command will be matched against rules and either executed (mocked) or rejected.
    Credits are deducted only on successful execution.
    """
    client_ip = request.client.host if request.client else None
    
    result = submit_command(db, current_user, cmd.command, ip_address=client_ip)
    
    return result.to_dict()


@app.get("/credits", response_model=CreditsResponse, tags=["Credits"])
async def get_credits(
    current_user: User = Depends(get_current_user)
):
    """Get current user's credit balance."""
    return {
        "credits": current_user.credits,
        "username": current_user.username
    }


@app.get("/history", tags=["Commands"])
async def get_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get command history for the current user."""
    commands = get_user_commands(db, current_user, limit)
    return {
        "commands": [cmd.to_dict() for cmd in commands],
        "total": len(commands)
    }


@app.get("/me", tags=["Users"])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user.to_dict()


# ==================== Admin Endpoints ====================

@app.post("/rules", tags=["Rules"])
async def create_rule_endpoint(
    rule_data: RuleCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new rule (Admin only)."""
    rule, error = create_rule(
        db,
        pattern=rule_data.pattern,
        action=rule_data.action,
        priority=rule_data.priority,
        description=rule_data.description,
        created_by=current_user.id
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    log_audit(db, current_user, "CREATE_RULE", 
              details=f"Created rule: {rule_data.pattern} -> {rule_data.action}")
    db.commit()
    db.refresh(rule)
    
    return {"message": "Rule created", "rule": rule.to_dict()}


@app.get("/rules", tags=["Rules"])
async def get_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all rules (sorted by priority)."""
    rules = get_sorted_rules(db)
    return {
        "rules": [rule.to_dict() for rule in rules],
        "total": len(rules)
    }


@app.delete("/rules/{rule_id}", tags=["Rules"])
async def delete_rule_endpoint(
    rule_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a rule (Admin only)."""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    pattern = rule.pattern
    success, error = delete_rule(db, rule_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    log_audit(db, current_user, "DELETE_RULE", details=f"Deleted rule: {pattern}")
    db.commit()
    
    return {"message": "Rule deleted"}


@app.post("/users", tags=["Users"])
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user (Admin only).
    
    Returns the API key only once - it cannot be retrieved later.
    """
    # Check if username exists
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Generate API key
    api_key = User.generate_api_key()
    
    # Create user
    user = User(
        username=user_data.username,
        api_key=api_key,
        role=user_data.role,
        credits=user_data.credits
    )
    db.add(user)
    
    log_audit(db, current_user, "CREATE_USER", 
              details=f"Created user: {user_data.username} ({user_data.role})")
    db.commit()
    db.refresh(user)
    
    # Return user with API key (shown only once)
    return {
        "message": "User created",
        "user": user.to_dict(include_api_key=True),
        "warning": "Save the API key now - it will not be shown again!"
    }


@app.get("/users", tags=["Users"])
async def get_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all users (Admin only)."""
    users = db.query(User).all()
    
    # Count commands per user
    user_list = []
    for user in users:
        user_dict = user.to_dict()
        user_dict["command_count"] = db.query(Command).filter(
            Command.user_id == user.id
        ).count()
        user_list.append(user_dict)
    
    return {
        "users": user_list,
        "total": len(users)
    }


@app.put("/users/{user_id}/credits", tags=["Users"])
async def adjust_user_credits(
    user_id: int,
    credit_data: CreditAdjust,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Adjust a user's credit balance (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_credits = user.credits
    user.credits = credit_data.credits
    
    log_audit(db, current_user, "ADJUST_CREDITS",
              details=f"Adjusted credits for {user.username}: {old_credits} -> {credit_data.credits}")
    db.commit()
    
    return {
        "message": "Credits updated",
        "user": user.to_dict()
    }


@app.get("/audit-logs", tags=["Audit"])
async def get_audit_logs(
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get audit logs (Admin only)."""
    logs = db.query(AuditLog).order_by(
        AuditLog.created_at.desc()
    ).limit(limit).all()
    
    return {
        "logs": [log.to_dict() for log in logs],
        "total": len(logs)
    }


@app.get("/commands/all", tags=["Commands"])
async def get_all_commands_endpoint(
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all commands from all users (Admin only)."""
    commands = get_all_commands(db, limit)
    return {
        "commands": [cmd.to_dict() for cmd in commands],
        "total": len(commands)
    }


# ==================== Health Check ====================

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "command-gateway"}


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Command Gateway API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# ==================== Run Server ====================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
