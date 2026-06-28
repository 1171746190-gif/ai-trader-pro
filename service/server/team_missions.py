"""Team missions business logic."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import get_db_connection, query_one, query_all, execute_sql

logger = logging.getLogger(__name__)


class TeamMissionError(Exception):
    """Team mission business logic error."""
    pass


class TeamMissionNotFound(TeamMissionError):
    """Team mission not found."""
    pass


# ==================== CRUD Operations ====================

def create_team_mission(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new team mission."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO challenges (challenge_key, title, description, market, start_at, end_at, initial_balance, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active', datetime('now'))
    """, (
        data.get("mission_key"),
        data.get("title"),
        data.get("description", ""),
        data.get("market", "us-stock"),
        data.get("start_at"),
        data.get("end_at"),
        data.get("initial_balance", 100000),
    ))
    
    mission_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"mission_id": mission_id, "mission_key": data.get("mission_key"), "status": "created"}


def get_team_mission(mission_key: str) -> Dict[str, Any]:
    """Get team mission by key."""
    result = query_one(
        "SELECT * FROM challenges WHERE challenge_key = ?",
        (mission_key,)
    )
    if not result:
        raise TeamMissionNotFound(f"Mission {mission_key} not found")
    return dict(result)


def list_team_missions(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List team missions."""
    if status:
        return query_all(
            "SELECT * FROM challenges WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset)
        )
    return query_all(
        "SELECT * FROM challenges ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )


# ==================== Team Management ====================

def create_team_for_mission(mission_key: str, agent_id: int, name: str) -> Dict[str, Any]:
    """Create a team for a mission."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO teams (challenge_key, name, created_by, created_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (mission_key, name, agent_id))
    
    team_id = cursor.lastrowid
    
    # Add creator as team member
    cursor.execute("""
        INSERT INTO team_members (team_id, agent_id, role, joined_at)
        VALUES (?, ?, 'leader', datetime('now'))
    """, (team_id, agent_id))
    
    conn.commit()
    conn.close()
    
    return {"team_id": team_id, "name": name, "mission_key": mission_key}


def join_team(team_id: int, agent_id: int) -> Dict[str, Any]:
    """Join an existing team."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if already a member
    cursor.execute(
        "SELECT id FROM team_members WHERE team_id = ? AND agent_id = ?",
        (team_id, agent_id)
    )
    if cursor.fetchone():
        conn.close()
        return {"status": "already_member", "team_id": team_id}
    
    cursor.execute("""
        INSERT INTO team_members (team_id, agent_id, joined_at)
        VALUES (?, ?, datetime('now'))
    """, (team_id, agent_id))
    
    conn.commit()
    conn.close()
    
    return {"status": "joined", "team_id": team_id}


def join_team_mission(mission_key: str, agent_id: int) -> Dict[str, Any]:
    """Join a team mission as a participant."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if already participating
    cursor.execute(
        "SELECT id FROM challenge_participants WHERE challenge_key = ? AND agent_id = ?",
        (mission_key, agent_id)
    )
    if cursor.fetchone():
        conn.close()
        return {"status": "already_joined", "mission_key": mission_key}
    
    cursor.execute("""
        INSERT INTO challenge_participants (challenge_key, agent_id, current_balance, joined_at)
        VALUES (?, ?, (SELECT initial_balance FROM challenges WHERE challenge_key = ?), datetime('now'))
    """, (mission_key, agent_id, mission_key))
    
    conn.commit()
    conn.close()
    
    return {"status": "joined", "mission_key": mission_key}


def get_team(team_id: int) -> Dict[str, Any]:
    """Get team details."""
    team = query_one("SELECT * FROM teams WHERE id = ?", (team_id,))
    if not team:
        raise TeamMissionNotFound(f"Team {team_id} not found")
    
    members = query_all(
        "SELECT tm.*, a.name as agent_name FROM team_members tm JOIN agents a ON tm.agent_id = a.id WHERE tm.team_id = ?",
        (team_id,)
    )
    
    return {"team": dict(team), "members": members}


def get_mission_teams(mission_key: str) -> List[Dict[str, Any]]:
    """Get all teams for a mission."""
    return query_all(
        "SELECT * FROM teams WHERE challenge_key = ? OR mission_key = ?",
        (mission_key, mission_key)
    )


# ==================== Auto Team Formation ====================

def auto_form_teams(mission_key: str, team_size: int = 3) -> List[Dict[str, Any]]:
    """Automatically form balanced teams for a mission."""
    # Get all participants without teams
    participants = query_all(
        """
        SELECT cp.agent_id, a.name, a.points
        FROM challenge_participants cp
        JOIN agents a ON cp.agent_id = a.id
        WHERE cp.challenge_key = ?
        AND cp.agent_id NOT IN (
            SELECT agent_id FROM team_members tm
            JOIN teams t ON tm.team_id = t.id
            WHERE t.challenge_key = ?
        )
        """,
        (mission_key, mission_key)
    )
    
    if not participants:
        return []
    
    # Sort by points for balanced teams
    participants.sort(key=lambda p: p.get("points", 0), reverse=True)
    
    teams = []
    current_team = []
    
    for p in participants:
        current_team.append(p)
        if len(current_team) >= team_size:
            teams.append(current_team)
            current_team = []
    
    if current_team:
        teams.append(current_team)
    
    # Create teams in database
    created_teams = []
    for i, members in enumerate(teams):
        team = create_team_for_mission(
            mission_key,
            members[0]["agent_id"],
            f"AutoTeam-{i+1}"
        )
        for member in members[1:]:
            join_team(team["team_id"], member["agent_id"])
        created_teams.append(team)
    
    return created_teams


# ==================== Submissions & Leaderboard ====================

def get_team_submissions(mission_key: str) -> List[Dict[str, Any]]:
    """Get all team submissions for a mission."""
    return query_all(
        """
        SELECT ct.*, a.name as agent_name
        FROM challenge_trades ct
        JOIN agents a ON ct.agent_id = a.id
        WHERE ct.challenge_key = ?
        ORDER BY ct.created_at DESC
        """,
        (mission_key,)
    )


def get_team_mission_leaderboard(mission_key: str) -> List[Dict[str, Any]]:
    """Get leaderboard for a team mission."""
    return query_all(
        """
        SELECT 
            t.id as team_id,
            t.name as team_name,
            COUNT(DISTINCT tm.agent_id) as member_count,
            SUM(ct.pnl) as total_pnl,
            COUNT(ct.id) as trade_count
        FROM teams t
        LEFT JOIN team_members tm ON t.id = tm.team_id
        LEFT JOIN challenge_trades ct ON t.challenge_key = ct.challenge_key
            AND ct.agent_id IN (SELECT agent_id FROM team_members WHERE team_id = t.id)
        WHERE t.challenge_key = ?
        GROUP BY t.id
        ORDER BY total_pnl DESC
        """,
        (mission_key,)
    )


# ==================== Settlement ====================

def settle_team_mission(mission_key: str) -> Dict[str, Any]:
    """Settle a team mission and calculate final scores."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update challenge status
    cursor.execute(
        "UPDATE challenges SET status = 'settled' WHERE challenge_key = ?",
        (mission_key,)
    )
    
    # Calculate final rankings
    leaderboard = get_team_mission_leaderboard(mission_key)
    
    for i, team in enumerate(leaderboard):
        cursor.execute(
            "UPDATE challenge_participants SET rank = ? WHERE challenge_key = ? AND agent_id IN (SELECT agent_id FROM team_members WHERE team_id = ?)",
            (i + 1, mission_key, team["team_id"])
        )
    
    conn.commit()
    conn.close()
    
    return {
        "status": "settled",
        "mission_key": mission_key,
        "teams_ranked": len(leaderboard),
    }


# ==================== Agent Missions ====================

def get_agent_team_missions(agent_id: int) -> List[Dict[str, Any]]:
    """Get all team missions for an agent."""
    return query_all(
        """
        SELECT c.* FROM challenges c
        JOIN challenge_participants cp ON c.challenge_key = cp.challenge_key
        WHERE cp.agent_id = ?
        ORDER BY c.created_at DESC
        """,
        (agent_id,)
    )


def link_signal_to_team(signal_id: int, team_id: int) -> bool:
    """Link a signal to a team submission."""
    try:
        execute_sql(
            "UPDATE signals SET team_id = ? WHERE id = ?",
            (team_id, signal_id)
        )
        return True
    except Exception as e:
        logger.error("Failed to link signal to team: %s", e)
        return False
