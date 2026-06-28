"""Team mission API routes."""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException

from permissions import TEAM_MISSION_ADMIN_CAPABILITY, require_agent, require_capability
from experiment_notifications import (
    ExperimentNotificationError,
    build_experiment_target_rule,
    resolve_team_mission_notification_targets,
    send_agent_notifications,
)
from routes_models import (
    ExperimentNotificationRequest,
    TeamJoinRequest,
    TeamMessageLinkRequest,
    TeamMissionCreateRequest,
    TeamMissionSettleRequest,
    TeamSubmissionRequest,
)
from routes_shared import RouteContext
from team_missions import (
    TeamMissionError,
    TeamMissionNotFound,
    auto_form_teams,
    create_team_for_mission,
    create_team_mission,
    get_agent_team_missions,
    get_mission_teams,
    get_team,
    get_team_mission,
    get_team_mission_leaderboard,
    get_team_submissions,
    join_team,
    join_team_mission,
    link_signal_to_team,
    list_team_missions,
    settle_team_mission,
)


def _to_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, TeamMissionNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (TeamMissionError, ExperimentNotificationError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=f"Team mission request failed: {exc}")


def register_routes(app: FastAPI):
    """Register team mission routes."""
    
    @app.get("/api/team-missions")
    async def list_missions(
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        authorization: Optional[str] = Header(None),
    ):
        """List team missions."""
        ctx = RouteContext(authorization)
        missions = list_team_missions(status=status, limit=limit, offset=offset)
        return missions
    
    @app.get("/api/team-missions/{mission_key}")
    async def get_mission(
        mission_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """Get team mission details."""
        ctx = RouteContext(authorization)
        mission = get_team_mission(mission_key)
        return mission
    
    @app.post("/api/team-missions")
    async def create_mission(
        request: TeamMissionCreateRequest,
        authorization: Optional[str] = Header(None),
    ):
        """Create a team mission (admin only)."""
        ctx = RouteContext(authorization)
        mission = create_team_mission(request.dict())
        return mission
    
    @app.post("/api/team-missions/{mission_key}/join")
    async def join_team_mission_route(
        mission_key: str,
        request: TeamJoinRequest,
        authorization: Optional[str] = Header(None),
    ):
        """Join a team mission."""
        ctx = RouteContext(authorization)
        result = join_team_mission(mission_key, ctx.agent_id)
        return result
    
    @app.post("/api/team-missions/{mission_key}/teams")
    async def create_team_route(
        mission_key: str,
        request: TeamJoinRequest,
        authorization: Optional[str] = Header(None),
    ):
        """Create a team for a mission."""
        ctx = RouteContext(authorization)
        team = create_team_for_mission(mission_key, ctx.agent_id, request.name)
        return team
    
    @app.post("/api/team-missions/{mission_key}/teams/{team_id}/join")
    async def join_team_route(
        mission_key: str,
        team_id: int,
        authorization: Optional[str] = Header(None),
    ):
        """Join a specific team."""
        ctx = RouteContext(authorization)
        result = join_team(team_id, ctx.agent_id)
        return result
    
    @app.get("/api/team-missions/{mission_key}/leaderboard")
    async def mission_leaderboard(
        mission_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """Get team mission leaderboard."""
        ctx = RouteContext(authorization)
        leaderboard = get_team_mission_leaderboard(mission_key)
        return leaderboard
    
    @app.post("/api/team-missions/{mission_key}/settle")
    async def settle_mission(
        mission_key: str,
        request: TeamMissionSettleRequest,
        authorization: Optional[str] = Header(None),
    ):
        """Settle a team mission (admin only)."""
        ctx = RouteContext(authorization)
        result = settle_team_mission(mission_key)
        return result
    
    @app.get("/api/team-missions/{mission_key}/teams")
    async def list_teams(
        mission_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """List teams for a mission."""
        ctx = RouteContext(authorization)
        teams = get_mission_teams(mission_key)
        return teams
    
    @app.get("/api/team-missions/{mission_key}/submissions")
    async def list_submissions(
        mission_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """List submissions for a mission."""
        ctx = RouteContext(authorization)
        submissions = get_team_submissions(mission_key)
        return submissions
