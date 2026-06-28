"""Challenge API routes."""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

from permissions import is_admin, is_experiment_admin


# ==================== Request Models ====================

class CreateChallengeRequest(BaseModel):
    challenge_key: str
    title: str
    description: Optional[str] = ""
    market: str = "us-stock"
    start_at: str
    end_at: str
    initial_balance: float = 100000


class JoinChallengeRequest(BaseModel):
    agent_id: int


class ChallengeTradeRequest(BaseModel):
    action: str
    symbol: str
    price: float
    quantity: float
    executed_at: str = "now"


# ==================== Routes ====================

def register_routes(app: FastAPI):
    """Register challenge routes."""
    
    @app.get("/api/challenges")
    async def list_challenges(
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ):
        """List challenges."""
        from challenges import get_challenges
        return get_challenges(status=status, limit=limit, offset=offset)
    
    @app.post("/api/challenges")
    async def create_challenge(
        request: CreateChallengeRequest,
        authorization: Optional[str] = Header(None),
    ):
        """Create a new challenge (admin only)."""
        # Verify admin
        # ...
        from challenges import create_challenge
        return create_challenge(request.dict())
    
    @app.get("/api/challenges/{challenge_key}")
    async def get_challenge(challenge_key: str):
        """Get challenge details."""
        from challenges import get_challenge_by_key
        return get_challenge_by_key(challenge_key)
    
    @app.post("/api/challenges/{challenge_key}/join")
    async def join_challenge(
        challenge_key: str,
        request: JoinChallengeRequest,
        authorization: Optional[str] = Header(None),
    ):
        """Join a challenge."""
        from challenges import join_challenge
        return join_challenge(challenge_key, request.agent_id)
    
    @app.post("/api/challenges/{challenge_key}/trade")
    async def challenge_trade(
        challenge_key: str,
        request: ChallengeTradeRequest,
        authorization: Optional[str] = Header(None),
    ):
        """Execute a trade within a challenge."""
        from challenges import execute_challenge_trade
        return execute_challenge_trade(challenge_key, request.dict())
    
    @app.get("/api/challenges/{challenge_key}/leaderboard")
    async def challenge_leaderboard(
        challenge_key: str,
        metric: str = "return",
        limit: int = 20,
    ):
        """Get challenge leaderboard."""
        from challenges import get_leaderboard
        return get_leaderboard(challenge_key, metric=metric, limit=limit)
    
    @app.get("/api/challenges/{challenge_key}/portfolio")
    async def challenge_portfolio(
        challenge_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """Get portfolio for a challenge."""
        from challenges get_portfolio
        return get_portfolio(challenge_key)
    
    @app.post("/api/challenges/{challenge_key}/teams")
    async def create_team(
        challenge_key: str,
        name: str,
        authorization: Optional[str] = Header(None),
    ):
        """Create a team for a challenge."""
        from challenges import create_team
        return create_team(challenge_key, name)
    
    @app.post("/api/challenges/{challenge_key}/teams/{team_id}/join")
    async def join_team(
        challenge_key: str,
        team_id: int,
        authorization: Optional[str] = Header(None),
    ):
        """Join a team."""
        from challenges import join_team
        return join_team(challenge_key, team_id)
    
    @app.get("/api/challenges/{challenge_key}/team-leaderboard")
    async def team_leaderboard(
        challenge_key: str,
        limit: int = 20,
    ):
        """Get team leaderboard."""
        from challenges import get_team_leaderboard
        return get_team_leaderboard(challenge_key, limit=limit)
    
    @app.post("/api/challenges/{challenge_key}/settle")
    async def settle_challenge(
        challenge_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """Settle a challenge (admin only)."""
        from challenges import settle_challenge
        return settle_challenge(challenge_key)
    
    @app.post("/api/challenges/{challenge_key}/cancel")
    async def cancel_challenge(
        challenge_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """Cancel a challenge (admin only)."""
        from challenges import cancel_challenge
        return cancel_challenge(challenge_key)
