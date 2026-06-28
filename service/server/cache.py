import functools
import json
import logging
import time
from typing import Any, Dict, Optional

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

# ==================== Connection ====================

def get_redis_client():
    """Get Redis client from config."""
    try:
        from config import get_config
        cfg = get_config()
        redis_url = cfg.get("redis_url")
        if redis_url and redis:
            return redis.from_url(redis_url, decode_responses=True)
    except Exception:
        pass
    return None


# ==================== Cache Decorator ====================

def cache_result(ttl: int = 300, key_prefix: str = "cache"):
    """Decorator to cache function result."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = get_redis_client()
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            if client:
                try:
                    cached = client.get(cache_key)
                    if cached:
                        return json.loads(cached)
                except Exception as e:
                    logger.warning("Cache read error: %s", e)
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            if client and result is not None:
                try:
                    client.setex(cache_key, ttl, json.dumps(result))
                except Exception as e:
                    logger.warning("Cache write error: %s", e)
            
            return result
        return wrapper
    return decorator


# ==================== Direct Cache Operations ====================

def cache_get(key: str) -> Optional[Any]:
    """Get value from cache."""
    client = get_redis_client()
    if not client:
        return None
    try:
        value = client.get(key)
        return json.loads(value) if value else None
    except Exception as e:
        logger.warning("Cache get error: %s", e)
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Set value in cache."""
    client = get_redis_client()
    if not client:
        return False
    try:
        client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.warning("Cache set error: %s", e)
        return False


def cache_delete(key: str) -> bool:
    """Delete key from cache."""
    client = get_redis_client()
    if not client:
        return False
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.warning("Cache delete error: %s", e)
        return False


# ==================== Status ====================

def get_cache_status() -> Dict[str, Any]:
    """Get cache system status."""
    try:
        from config import get_config
        cfg = get_config()
        redis_url = cfg.get("redis_url")
        redis_enabled = cfg.get("redis_enabled", False)
        
        status = {
            "enabled": redis_enabled,
            "configured": bool(redis_url),
            "available": False,
            "prefix": "aitrader",
            "client_installed": redis is not None,
            "last_error": None,
        }
        
        if redis_enabled and redis_url and redis:
            try:
                client = redis.from_url(redis_url)
                client.ping()
                status["available"] = True
            except Exception as e:
                status["last_error"] = str(e)
        
        return status
    except Exception as e:
        return {
            "enabled": False,
            "configured": False,
            "available": False,
            "error": str(e),
        }
