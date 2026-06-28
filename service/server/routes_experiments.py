"""Experiment and reward API routes."""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# ==================== Request Models ====================

class CreateExperimentRequest(BaseModel):
    experiment_key: str
    name: str
    description: Optional[str] = ""
    target_type: str = "agent"
    status: str = "active"
    variants: List[Dict[str, Any]]


class AssignVariantRequest(BaseModel):
    agent_id: int


# ==================== Routes ====================

def register_routes(app: FastAPI):
    """Register experiment routes."""
    
    @app.get("/api/experiments")
    async def list_experiments(
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ):
        """List experiments."""
        from experiments import get_experiments
        return get_experiments(status=status, limit=limit, offset=offset)
    
    @app.post("/api/experiments")
    async def create_experiment(
        request: CreateExperimentRequest,
        authorization: Optional[str] = Header(None),
    ):
        """Create a new experiment (admin only)."""
        from experiments import create_experiment
        return create_experiment(request.dict())
    
    @app.get("/api/experiments/{experiment_key}")
    async def get_experiment(experiment_key: str):
        """Get experiment details."""
        from experiments import get_experiment_by_key
        return get_experiment_by_key(experiment_key)
    
    @app.post("/api/experiments/{experiment_key}/assign")
    async def assign_variant(
        experiment_key: str,
        request: AssignVariantRequest,
    ):
        """Assign a variant to an agent."""
        from experiments import assign_variant
        return assign_variant(experiment_key, request.agent_id)
    
    @app.get("/api/agents/me/experiments")
    async def my_experiments(
        authorization: Optional[str] = Header(None),
    ):
        """Get experiments for current agent."""
        # Extract agent from token
        from experiments import get_agent_experiments
        return get_agent_experiments(authorization)
    
    @app.get("/api/experiments/{experiment_key}/challenge-report")
    async def experiment_challenge_report(
        experiment_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """Get challenge report for an experiment."""
        from experiments import get_challenge_report
        return get_challenge_report(experiment_key)
    
    @app.get("/api/experiments/{experiment_key}/metrics")
    async def experiment_metrics(
        experiment_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """Get experiment metrics."""
        from experiment_metrics import get_metrics
        return get_metrics(experiment_key)
    
    @app.get("/api/experiments/{experiment_key}/notifications")
    async def experiment_notifications(
        experiment_key: str,
        authorization: Optional[str] = Header(None),
    ):
        """Get experiment notifications."""
        from experiment_notifications import get_notifications
        return get_notifications(experiment_key)
