from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response


def register_routes(app: FastAPI):
    """Register miscellaneous routes."""
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from datetime import datetime, timezone
        return {
            "status": "ok",
            "service": "ai-trader-pro",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "AI-Trader Pro",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }
    
    @app.get("/SKILL.md")
    async def skill_md():
        """Serve SKILL.md for agent integration."""
        skill_path = Path(__file__).parent.parent.parent / "SKILL.md"
        if skill_path.exists():
            return FileResponse(skill_path, media_type="text/markdown")
        return Response("SKILL.md not found", status_code=404)
