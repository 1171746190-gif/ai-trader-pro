import os
from typing import Any, Dict, Optional


# ==================== Config Loader ====================

def get_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    return {
        # Environment
        "environment": os.getenv("ENVIRONMENT", "development"),
        
        # Database
        "database_url": os.getenv("DATABASE_URL", ""),
        "db_path": os.getenv("DB_PATH", "service/server/data/clawtrader.db"),
        
        # API Keys
        "alpha_vantage_api_key": os.getenv("ALPHA_VANTAGE_API_KEY", "demo"),
        "adanos_api_key": os.getenv("ADANOS_API_KEY", ""),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        
        # CORS
        "cors_origins": os.getenv("CLAWTRADER_CORS_ORIGINS", "http://localhost:3000"),
        
        # Redis
        "redis_enabled": os.getenv("REDIS_ENABLED", "false").lower() in ("true", "1", "yes"),
        "redis_url": os.getenv("REDIS_URL", ""),
        
        # Intervals
        "position_refresh_interval": int(os.getenv("POSITION_REFRESH_INTERVAL", "300")),
        "market_news_refresh_interval": int(os.getenv("MARKET_NEWS_REFRESH_INTERVAL", "900")),
        
        # Admin
        "admin_agents": os.getenv("AI_TRADER_ADMIN_AGENTS", ""),
        
        # Background tasks
        "background_tasks": os.getenv("AI_TRADER_BACKGROUND_TASKS", ""),
        "worker_nice": int(os.getenv("AI_TRADER_WORKER_NICE", "10")),
    }


def get_env() -> str:
    """Get current environment."""
    return os.getenv("ENVIRONMENT", "development")


def is_production() -> bool:
    """Check if running in production."""
    return get_env() == "production"


def is_development() -> bool:
    """Check if running in development."""
    return get_env() == "development"
