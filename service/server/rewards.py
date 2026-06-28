import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ==================== Reward Constants ====================

POINTS_STRATEGY = 10
POINTS_OPERATION = 10
POINTS_DISCUSSION = 4
POINTS_FOLLOWER_SIGNAL_RECEIVED = 1

QUALITY_WEIGHT_MULTIPLIER = 1.5


# ==================== Points Calculation ====================

def calculate_strategy_points(quality_score: float = 0) -> int:
    """Calculate points for publishing a strategy signal."""
    base = POINTS_STRATEGY
    if quality_score > 0:
        bonus = int(quality_score * 2)
        return base + bonus
    return base


def calculate_operation_points(quality_score: float = 0) -> int:
    """Calculate points for publishing an operation signal."""
    base = POINTS_OPERATION
    if quality_score > 0:
        bonus = int(quality_score * 2)
        return base + bonus
    return base


def calculate_discussion_points(quality_score: float = 0) -> int:
    """Calculate points for publishing a discussion."""
    base = POINTS_DISCUSSION
    if quality_score > 0:
        bonus = int(quality_score * 1)
        return base + bonus
    return base


def calculate_follower_points(follower_count: int) -> int:
    """Calculate points when followers receive signals."""
    return follower_count * POINTS_FOLLOWER_SIGNAL_RECEIVED


# ==================== Quality-Weighted Rewards ====================

def apply_quality_multiplier(points: int, quality_score: float, multiplier: float = QUALITY_WEIGHT_MULTIPLIER) -> int:
    """Apply quality multiplier to points (for experiment variants)."""
    if quality_score >= 4:
        return int(points * multiplier)
    elif quality_score >= 3:
        return int(points * (1 + (multiplier - 1) * 0.5))
    return points


# ==================== Database Operations ====================

def record_points_transaction(
    agent_id: int,
    points: int,
    transaction_type: str,
    reference_id: Optional[int] = None,
    db=None
) -> bool:
    """Record a points transaction in database."""
    try:
        if db is None:
            from database import get_db
            db = get_db()
        
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO points_transactions (agent_id, points, type, reference_id, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (agent_id, points, transaction_type, reference_id)
        )
        
        # Update agent points
        cursor.execute(
            "UPDATE agents SET points = COALESCE(points, 0) + ? WHERE id = ?",
            (points, agent_id)
        )
        
        db.commit()
        return True
    except Exception as e:
        logger.error("Failed to record points: %s", e)
        return False


def get_agent_points(agent_id: int, db=None) -> int:
    """Get total points for an agent."""
    try:
        if db is None:
            from database import get_db
            db = get_db()
        
        cursor = db.cursor()
        cursor.execute("SELECT COALESCE(points, 0) FROM agents WHERE id = ?", (agent_id,))
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception as e:
        logger.error("Failed to get points: %s", e)
        return 0
