"""Experiment events tracking."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import get_db_connection

logger = logging.getLogger(__name__)


def record_event(
    experiment_key: str,
    event_type: str,
    agent_id: int,
    payload: Optional[Dict[str, Any]] = None,
) -> bool:
    """Record an experiment event.
    
    Args:
        experiment_key: The experiment identifier
        event_type: Type of event (e.g., 'variant_assigned', 'signal_published')
        agent_id: The agent involved
        payload: Additional event data
    
    Returns:
        True if recorded successfully
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO experiment_events (experiment_key, event_type, agent_id, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            experiment_key,
            event_type,
            agent_id,
            json.dumps(payload) if payload else None,
            datetime.now(timezone.utc).isoformat(),
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error("Failed to record event: %s", e)
        return False


def get_events(
    experiment_key: str,
    event_type: Optional[str] = None,
    agent_id: Optional[int] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Get experiment events with optional filtering."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM experiment_events WHERE experiment_key = ?"
    params = [experiment_key]
    
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    
    if agent_id:
        query += " AND agent_id = ?"
        params.append(agent_id)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return rows


def get_event_summary(experiment_key: str) -> Dict[str, Any]:
    """Get summary statistics for experiment events."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_events,
            COUNT(DISTINCT agent_id) as unique_agents,
            COUNT(DISTINCT event_type) as event_types
        FROM experiment_events
        WHERE experiment_key = ?
    """, (experiment_key,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return {"total_events": 0, "unique_agents": 0, "event_types": 0}


# Lazy import to avoid circular dependency
import json
