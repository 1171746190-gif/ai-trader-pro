from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_config
from routes_agent import router as agent_router
from routes_challenges import router as challenges_router
from routes_experiments import router as experiments_router
from routes_market import router as market_router
from routes_misc import router as misc_router
from routes_research import router as research_router
from routes_signals import router as signals_router
from routes_trading import router as trading_router
from routes_users import router as users_router


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    cfg = get_config()
    
    app = FastAPI(
        title="AI-Trader Pro",
        description="AI Agent Native Trading Platform",
        version="1.0.0",
    )
    
    # CORS
    origins = [o.strip() for o in cfg.get("cors_origins", "http://localhost:3000").split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(agent_router, prefix="/api/claw")
    app.include_router(signals_router, prefix="/api/signals")
    app.include_router(challenges_router, prefix="/api/challenges")
    app.include_router(experiments_router, prefix="/api/experiments")
    app.include_router(market_router, prefix="/api/market-intel")
    app.include_router(trading_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(research_router, prefix="/api/research")
    app.include_router(misc_router)
    
    return app
