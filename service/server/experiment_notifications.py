"""Experiment notification system."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExperimentNotificationError(Exception):
    """Error sending experiment notifications."""
    pass


def build_experiment_target_rule(
    experiment_key: str,
    variant_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a target rule for experiment notifications.
    
    Args:
        experiment_key: The experiment identifier
        variant_key: Optional variant to target
    
    Returns:
        Target rule dict
    """
    rule = {
        "type": "experiment",
        "experiment_key": experiment_key,
    }
    if variant_key:
        rule["variant_key"] = variant_key
    return rule


def resolve_team_mission_notification_targets(
    mission_key: str,
    team_id: Optional[int] = None,
) -> List[int]:
    """Resolve notification targets for a team mission.
    
    Args:
        mission_key: The mission identifier
        team_id: Optional specific team
    
    Returns:
        List of agent IDs to notify
    """
    from database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if team_id:
        cursor.execute(
            "SELECT agent_id FROM team_members WHERE team_id = ?",
            (team_id,)
        )
    else:
        cursor.execute("""
            SELECT tm.agent_id 
            FROM team_members tm
            JOIN teams t ON tm.team_id = t.id
            WHERE t.mission_key = ?
        """, (mission_key,))
    
    agent_ids = [row["agent_id"] for row in cursor.fetchall()]
    conn.close()
    
    return agent_ids


def send_agent_notifications(
    agent_ids: List[int],
    message: str,
    notification_type: str = "experiment",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send notifications to agents.
    
    Args:
        agent_ids: List of agent IDs
        message: Notification message
        notification_type: Type of notification
        metadata: Additional metadata
    
    Returns:
        Summary of sent notifications
    """
    from database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sent = 0
    failed = 0
    
    for agent_id in agent_ids:
        try:
            cursor.execute("""
                INSERT INTO notifications (agent_id, type, message, metadata, is_read, created_at)
                VALUES (?, ?, ?, ?, 0, datetime('now'))
            """, (agent_id, notification_type, message, json.dumps(metadata) if metadata else None))
            sent += 1
        except Exception as e:
            logger.error("Failed to send notification to agent %s: %s", agent_id, e)
            failed += 1
    
    conn.commit()
    conn.close()
    
    return {"sent": sent, "failed": failed, "total": len(agent_ids)}


def get_unread_notifications(agent_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Get unread notifications for an agent."""
    from database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM notifications
        WHERE agent_id = ? AND is_read = 0
        ORDER BY created_at DESC
        LIMIT ?
    """, (agent_id, limit))
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return rows


def mark_notifications_read(agent_id: int, notification_ids: Optional[List[int]] = None) -> int:
    """Mark notifications as read.
    
    Returns number of notifications marked as read.
    """
    from database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if notification_ids:
        placeholders = ','.join('?' * len(notification_ids))
        cursor.execute(f"""
            UPDATE notifications SET is_read = 1
            WHERE agent_id = ? AND id IN ({placeholders})
        """, [agent_id] + notification_ids)
    else:
        cursor.execute("""
            UPDATE notifications SET is_read = 1
            WHERE agent_id = ? AND is_read = 0
        """, (agent_id,))
    
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return count


# Lazy import
import json
