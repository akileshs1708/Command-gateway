# backend/rules.py
# Rule matching logic (regex engine)

import re
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from models import Rule

class RuleMatchResult:
    """Result of rule matching operation."""
    def __init__(
        self,
        matched: bool,
        rule: Optional[Rule] = None,
        action: Optional[str] = None,
        pattern: Optional[str] = None
    ):
        self.matched = matched
        self.rule = rule
        self.action = action
        self.pattern = pattern


def get_sorted_rules(db: Session) -> List[Rule]:
    """
    Get all rules sorted by priority (ascending).
    Lower priority number = higher precedence.
    """
    return db.query(Rule).order_by(Rule.priority.asc()).all()


def match_command(db: Session, command: str) -> RuleMatchResult:
    """
    Match a command against all rules.
    Returns the first matching rule based on priority.
    
    Rules are evaluated in priority order (lowest number first).
    If no rule matches, returns a non-matched result.
    """
    rules = get_sorted_rules(db)
    
    for rule in rules:
        try:
            # Compile regex pattern (case-insensitive)
            pattern = re.compile(rule.pattern, re.IGNORECASE)
            
            # Check if command matches the pattern
            if pattern.search(command):
                return RuleMatchResult(
                    matched=True,
                    rule=rule,
                    action=rule.action,
                    pattern=rule.pattern
                )
        except re.error as e:
            # Skip invalid regex patterns (log in production)
            print(f"Invalid regex pattern '{rule.pattern}': {e}")
            continue
    
    # No rule matched
    return RuleMatchResult(matched=False)


def validate_regex_pattern(pattern: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a regex pattern.
    Returns (is_valid, error_message).
    """
    try:
        re.compile(pattern)
        return True, None
    except re.error as e:
        return False, str(e)


def create_rule(
    db: Session,
    pattern: str,
    action: str,
    priority: int = 10,
    description: Optional[str] = None,
    created_by: Optional[int] = None
) -> Tuple[Optional[Rule], Optional[str]]:
    """
    Create a new rule.
    Returns (rule, error_message).
    """
    # Validate action
    if action not in ["AUTO_ACCEPT", "AUTO_REJECT"]:
        return None, "Action must be 'AUTO_ACCEPT' or 'AUTO_REJECT'"
    
    # Validate regex pattern
    is_valid, error = validate_regex_pattern(pattern)
    if not is_valid:
        return None, f"Invalid regex pattern: {error}"
    
    # Create rule
    rule = Rule(
        pattern=pattern,
        action=action,
        priority=priority,
        description=description,
        created_by=created_by
    )
    
    db.add(rule)
    return rule, None


def delete_rule(db: Session, rule_id: int) -> Tuple[bool, Optional[str]]:
    """
    Delete a rule by ID.
    Returns (success, error_message).
    """
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    
    if not rule:
        return False, "Rule not found"
    
    db.delete(rule)
    return True, None


def get_default_rules() -> List[dict]:
    """
    Get default rules to seed the database.
    """
    return [
        {
            "pattern": r"rm\s+-rf\s+/",
            "action": "AUTO_REJECT",
            "priority": 1,
            "description": "Block recursive delete of root"
        },
        {
            "pattern": r"mkfs",
            "action": "AUTO_REJECT",
            "priority": 2,
            "description": "Block filesystem formatting"
        },
        {
            "pattern": r":\(\)\{\s*:\|:\&\s*\};:",
            "action": "AUTO_REJECT",
            "priority": 3,
            "description": "Block fork bomb"
        },
        {
            "pattern": r"dd\s+if=.*of=/dev/",
            "action": "AUTO_REJECT",
            "priority": 4,
            "description": "Block direct disk writes"
        },
        {
            "pattern": r"chmod\s+777\s+/",
            "action": "AUTO_REJECT",
            "priority": 5,
            "description": "Block chmod 777 on root"
        },
        {
            "pattern": r">\s*/dev/sd[a-z]",
            "action": "AUTO_REJECT",
            "priority": 6,
            "description": "Block writing to disk devices"
        },
        {
            "pattern": r"^git\s+(status|log|diff|branch|show)",
            "action": "AUTO_ACCEPT",
            "priority": 10,
            "description": "Allow safe git commands"
        },
        {
            "pattern": r"^(ls|cat|pwd|whoami|date|echo|hostname)",
            "action": "AUTO_ACCEPT",
            "priority": 11,
            "description": "Allow basic info commands"
        },
        {
            "pattern": r"^(grep|find|head|tail|wc|sort|uniq)",
            "action": "AUTO_ACCEPT",
            "priority": 12,
            "description": "Allow text processing commands"
        },
        {
            "pattern": r"^(ps|top|df|du|free|uptime)",
            "action": "AUTO_ACCEPT",
            "priority": 13,
            "description": "Allow system monitoring commands"
        }
    ]
