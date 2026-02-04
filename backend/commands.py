# backend/commands.py
# Command submission & execution logic

from typing import Tuple, Optional
from sqlalchemy.orm import Session
from models import User, Command, AuditLog
from rules import match_command, RuleMatchResult
from auth import deduct_credits, log_audit

class CommandResult:
    """Result of command submission."""
    def __init__(
        self,
        success: bool,
        command: Optional[Command] = None,
        status: Optional[str] = None,
        message: Optional[str] = None,
        credits_remaining: Optional[int] = None
    ):
        self.success = success
        self.command = command
        self.status = status
        self.message = message
        self.credits_remaining = credits_remaining
    
    def to_dict(self):
        return {
            "success": self.success,
            "command": self.command.to_dict() if self.command else None,
            "status": self.status,
            "message": self.message,
            "credits_remaining": self.credits_remaining
        }


def mock_execute_command(command_text: str) -> str:
    """
    Mock command execution.
    In a real system, this would execute the command.
    Here we just return a simulated output.
    """
    # Simulate different outputs based on command
    command_lower = command_text.lower().strip()
    
    if command_lower.startswith("ls"):
        return "file1.txt\nfile2.txt\ndir1/\ndir2/"
    elif command_lower.startswith("pwd"):
        return "/home/user/projects"
    elif command_lower.startswith("whoami"):
        return "gateway_user"
    elif command_lower.startswith("date"):
        from datetime import datetime
        return datetime.now().strftime("%a %b %d %H:%M:%S UTC %Y")
    elif command_lower.startswith("echo"):
        # Return everything after 'echo '
        return command_text[5:] if len(command_text) > 5 else ""
    elif command_lower.startswith("git status"):
        return "On branch main\nYour branch is up to date with 'origin/main'.\nnothing to commit, working tree clean"
    elif command_lower.startswith("git log"):
        return "commit abc123 (HEAD -> main)\nAuthor: User <user@example.com>\nDate: Today\n\n    Initial commit"
    elif command_lower.startswith("cat"):
        return "[Mock file content]\nLine 1\nLine 2\nLine 3"
    elif command_lower.startswith("hostname"):
        return "command-gateway-server"
    elif command_lower.startswith("uptime"):
        return " 14:30:00 up 30 days,  2:15,  1 user,  load average: 0.00, 0.01, 0.05"
    elif command_lower.startswith("df"):
        return "Filesystem     1K-blocks    Used Available Use% Mounted on\n/dev/sda1      100000000 50000000  50000000  50% /"
    elif command_lower.startswith("free"):
        return "              total        used        free\nMem:        8000000     4000000     4000000\nSwap:       2000000           0     2000000"
    elif command_lower.startswith("ps"):
        return "  PID TTY          TIME CMD\n    1 ?        00:00:01 init\n  100 pts/0    00:00:00 bash"
    else:
        return f"[Mocked execution of: {command_text}]\nCommand executed successfully."


def submit_command(
    db: Session,
    user: User,
    command_text: str,
    ip_address: Optional[str] = None
) -> CommandResult:
    """
    Submit a command for processing.
    
    This function handles the entire command flow:
    1. Check user credits
    2. Match command against rules
    3. Execute or reject based on rules
    4. Update credits (only on successful execution)
    5. Create audit log
    
    All operations are transactional - if any step fails, everything is rolled back.
    """
    try:
        # Step 1: Check if user has credits
        if user.credits <= 0:
            # Log the attempt but don't create command record
            log_audit(
                db, user, "COMMAND_REJECTED",
                command_text=command_text,
                details="Insufficient credits",
                ip_address=ip_address
            )
            db.commit()
            
            return CommandResult(
                success=False,
                status="rejected",
                message="Insufficient credits",
                credits_remaining=user.credits
            )
        
        # Step 2: Match command against rules
        match_result = match_command(db, command_text)
        
        # Step 3: Determine action based on match result
        if not match_result.matched:
            # No rule matched - reject by default
            status = "rejected"
            result_message = "No matching rule found - command rejected by default"
            credits_to_deduct = 0
            mock_output = None
        elif match_result.action == "AUTO_REJECT":
            # Rule explicitly rejects
            status = "rejected"
            result_message = f"Command rejected by rule: {match_result.pattern}"
            credits_to_deduct = 0
            mock_output = None
        elif match_result.action == "AUTO_ACCEPT":
            # Rule accepts - execute (mock)
            status = "executed"
            mock_output = mock_execute_command(command_text)
            result_message = f"Command executed successfully (matched rule: {match_result.pattern})"
            credits_to_deduct = 1
        else:
            # Unknown action - reject for safety
            status = "rejected"
            result_message = "Unknown rule action - command rejected"
            credits_to_deduct = 0
            mock_output = None
        
        # Step 4: Create command record
        command = Command(
            user_id=user.id,
            command_text=command_text,
            status=status,
            matched_rule_id=match_result.rule.id if match_result.rule else None,
            matched_pattern=match_result.pattern,
            credits_deducted=credits_to_deduct,
            result=mock_output
        )
        db.add(command)
        
        # Step 5: Deduct credits if command was executed
        if credits_to_deduct > 0:
            if not deduct_credits(db, user, credits_to_deduct):
                # This shouldn't happen since we checked credits earlier
                db.rollback()
                return CommandResult(
                    success=False,
                    status="rejected",
                    message="Credit deduction failed",
                    credits_remaining=user.credits
                )
        
        # Step 6: Create audit log
        log_audit(
            db, user,
            action="COMMAND_EXECUTED" if status == "executed" else "COMMAND_REJECTED",
            command_text=command_text,
            details=result_message,
            ip_address=ip_address
        )
        
        # Step 7: Commit transaction
        db.commit()
        db.refresh(command)
        db.refresh(user)
        
        return CommandResult(
            success=True,
            command=command,
            status=status,
            message=result_message,
            credits_remaining=user.credits
        )
        
    except Exception as e:
        # Rollback on any error
        db.rollback()
        
        # Log the error (in production, use proper logging)
        print(f"Command submission error: {e}")
        
        return CommandResult(
            success=False,
            status="rejected",
            message=f"Internal error: {str(e)}",
            credits_remaining=user.credits if user else None
        )


def get_user_commands(db: Session, user: User, limit: int = 50) -> list:
    """
    Get command history for a user.
    """
    return db.query(Command).filter(
        Command.user_id == user.id
    ).order_by(Command.created_at.desc()).limit(limit).all()


def get_all_commands(db: Session, limit: int = 100) -> list:
    """
    Get all commands (admin only).
    """
    return db.query(Command).order_by(Command.created_at.desc()).limit(limit).all()
