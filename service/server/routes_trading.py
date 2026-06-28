import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException


# ==================== Routes ====================

def register_routes(app: FastAPI):
    """Register trading-related routes."""
    
    @app.get("/api/profit/history")
    async def profit_history(
        days: int = 30,
        metric: str = "return",
        limit: int = 100,
        offset: int = 0,
        authorization: Optional[str] = Header(None),
    ):
        """Get profit/loss history."""
        from database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get profit history for specified days
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT * FROM profit_history
            WHERE created_at > ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (since, limit, offset))
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "items": rows,
            "total": len(rows),
            "metric": metric,
            "days": days,
        }
    
    @app.get("/api/portfolio")
    async def get_portfolio(
        authorization: Optional[str] = Header(None),
    ):
        """Get current portfolio."""
        agent = _get_agent_from_header(authorization)
        agent_id = agent["id"]
        
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get positions
        cursor.execute("""
            SELECT * FROM positions WHERE agent_id = ?
        """, (agent_id,))
        positions = [dict(row) for row in cursor.fetchall()]
        
        # Get agent info
        cursor.execute("SELECT cash_balance, points FROM agents WHERE id = ?", (agent_id,))
        agent_info = cursor.fetchone()
        
        conn.close()
        
        return {
            "agent_id": agent_id,
            "cash_balance": agent_info["cash_balance"] if agent_info else 0,
            "points": agent_info["points"] if agent_info else 0,
            "positions": positions,
            "position_count": len(positions),
        }
    
    @app.get("/api/positions")
    async def get_positions(
        market: Optional[str] = None,
        authorization: Optional[str] = Header(None),
    ):
        """Get positions with optional market filter."""
        agent = _get_agent_from_header(authorization)
        agent_id = agent["id"]
        
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if market:
            cursor.execute(
                "SELECT * FROM positions WHERE agent_id = ? AND market = ?",
                (agent_id, market)
            )
        else:
            cursor.execute("SELECT * FROM positions WHERE agent_id = ?", (agent_id,))
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"positions": rows, "count": len(rows)}
    
    @app.get("/api/trades")
    async def get_trades(
        limit: int = 50,
        offset: int = 0,
        authorization: Optional[str] = Header(None),
    ):
        """Get trade history."""
        agent = _get_agent_from_header(authorization)
        agent_id = agent["id"]
        
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM signals
            WHERE agent_id = ? AND message_type = 'operation'
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (agent_id, limit, offset))
        
        rows = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        cursor.execute(
            "SELECT COUNT(*) FROM signals WHERE agent_id = ? AND message_type = 'operation'",
            (agent_id,)
        )
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "trades": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    @app.get("/api/leaderboard")
    async def get_leaderboard(
        metric: str = "return",
        limit: int = 20,
        period: str = "all",
    ):
        """Get global leaderboard."""
        from database import get_db_connection
        from challenge_scoring import rank_participants
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all agents with their stats
        cursor.execute("""
            SELECT id, name, points, initial_balance, cash_balance,
                   (initial_balance - cash_balance) as pnl
            FROM agents
            ORDER BY points DESC
            LIMIT ?
        """, (limit,))
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Format as participants
        participants = []
        for row in rows:
            participants.append({
                "agent_id": row["id"],
                "agent_name": row["name"],
                "total_return": ((row["cash_balance"] - row["initial_balance"]) / row["initial_balance"] * 100) if row["initial_balance"] else 0,
                "points": row["points"],
            })
        
        ranked = rank_participants(participants, metric=metric)
        
        return {
            "participants": ranked,
            "metric": metric,
            "period": period,
        }


# ==================== Helper ====================

def _get_agent_from_header(authorization: Optional[str]):
    """Get agent from authorization header."""
    from routes_shared import get_current_agent
    return get_current_agent(authorization)
