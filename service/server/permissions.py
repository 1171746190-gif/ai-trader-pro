import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ==================== Role Definitions ====================

ROLES = {
    "admin": {
        "permissions": ["*"],  # All permissions
        "description": "Full system access",
    },
    "experiment_admin": {
        "permissions": [
            "experiments.create",
            "experiments.update",
            "experiments.delete",
            "experiments.settle",
            "experiments.report",
        ],
        "description": "Can manage experiments",
    },
    "researcher": {
        "permissions": [
            "research.export",
            "research.read",
        ],
        "description": "Can export research data",
    },
    "user": {
        "permissions": [
            "signals.read",
            "signals.create",
            "challenges.read",
            "challenges.join",
            "portfolio.read",
        ],
        "description": "Standard user access",
    },
}


# ==================== Permission Check ====================

def get_admin_agent_ids() -> List[str]:
    """Get list of admin agent IDs/names from environment."""
    admin_env = os.getenv("AI_TRADER_ADMIN_AGENTS", "")
    if not admin_env:
        return []
    return [a.strip() for a in admin_env.split(",") if a.strip()]


def is_admin(agent_id: int, agent_name: str) -> bool:
    """Check if agent has admin role."""
    admin_ids = get_admin_agent_ids()
    return str(agent_id) in admin_ids or agent_name in admin_ids


def is_experiment_admin(agent_id: int, agent_name: str) -> bool:
    """Check if agent has experiment admin role."""
    if is_admin(agent_id, agent_name):
        return True
    # Additional logic for experiment admins
    return False


def has_permission(agent_id: int, agent_name: str, permission: str) -> bool:
    """Check if agent has specific permission."""
    if is_admin(agent_id, agent_name):
        return True
    
    # Get agent role from database
    role = get_agent_role(agent_id)
    if not role:
        role = "user"
    
    role_perms = ROLES.get(role, {}).get("permissions", [])
    return permission in role_perms or "*" in role_perms


def get_agent_role(agent_id: int) -> Optional[str]:
    """Get role for an agent from database."""
    try:
        from database import get_db
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT role FROM agents WHERE id = ?", (agent_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.error("Failed to get agent role: %s", e)
        return None


# ==================== RBAC Decorator ====================

def require_permission(permission: str):
    """Decorator to require specific permission."""
    from functools import wraps
    from fastapi import HTTPException, Request
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and agent info
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request is None:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                agent_id = getattr(request.state, "agent_id", None)
                agent_name = getattr(request.state, "agent_name", "")
                
                if agent_id and has_permission(agent_id, agent_name, permission):
                    return await func(*args, **kwargs)
            
            raise HTTPException(status_code=403, detail="Permission denied")
        return wrapper
    return decorator
