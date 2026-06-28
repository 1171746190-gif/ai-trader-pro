import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ==================== Task Registry ====================

_registered_tasks = []
_background_tasks_started = False


# ==================== Task Decorator ====================

def register_task(name: str, interval: int = 300):
    """Register a background task."""
    def decorator(func):
        _registered_tasks.append({
            "name": name,
            "interval": interval,
            "func": func,
            "last_run": 0,
        })
        return func
    return decorator


# ==================== Built-in Tasks ====================

@register_task("prices", interval=300)
def task_update_prices():
    """Update position prices from market data."""
    try:
        from price_fetcher import update_all_prices
        update_all_prices()
        logger.debug("Price update completed")
    except Exception as e:
        logger.error("Price update failed: %s", e)


@register_task("profit_history", interval=60)
def task_record_profit_history():
    """Record profit/loss history snapshot."""
    try:
        from services import record_profit_snapshot
        record_profit_snapshot()
        logger.debug("Profit history recorded")
    except Exception as e:
        logger.error("Profit history recording failed: %s", e)


@register_task("settlements", interval=60)
def task_check_settlements():
    """Check and process Polymarket settlements."""
    try:
        from challenges import process_settlements
        process_settlements()
        logger.debug("Settlement check completed")
    except Exception as e:
        logger.error("Settlement check failed: %s", e)


@register_task("market_intel", interval=900)
def task_update_market_intel():
    """Update market intelligence data."""
    try:
        from market_intel import refresh_market_data
        refresh_market_data()
        logger.debug("Market intel updated")
    except Exception as e:
        logger.error("Market intel update failed: %s", e)


# ==================== Trending Cache ====================

def _update_trending_cache():
    """Initialize trending signals cache."""
    try:
        from services import update_trending
        update_trending()
    except Exception as e:
        logger.error("Trending cache update failed: %s", e)


# ==================== Background Task Control ====================

def background_tasks_enabled_for_api() -> bool:
    """Check if background tasks should run in API process."""
    import os
    tasks_env = os.getenv("AI_TRADER_BACKGROUND_TASKS", "")
    return bool(tasks_env)


def start_background_tasks(logger_instance=None) -> List[str]:
    """Start all registered background tasks."""
    global _background_tasks_started
    
    if _background_tasks_started:
        return []
    
    log = logger_instance or logger
    started = []
    
    for task in _registered_tasks:
        try:
            task["func"]()
            task["last_run"] = time.time()
            started.append(task["name"])
            log.info("Started background task: %s (interval: %ds)", task["name"], task["interval"])
        except Exception as e:
            log.error("Failed to start task %s: %s", task["name"], e)
    
    _background_tasks_started = True
    return started


def run_pending_tasks():
    """Run tasks that are due (called by worker loop)."""
    current_time = time.time()
    
    for task in _registered_tasks:
        if current_time - task["last_run"] >= task["interval"]:
            try:
                task["func"]()
                task["last_run"] = current_time
            except Exception as e:
                logger.error("Task %s failed: %s", task["name"], e)


def get_task_status() -> List[Dict[str, Any]]:
    """Get status of all registered tasks."""
    current_time = time.time()
    return [
        {
            "name": t["name"],
            "interval": t["interval"],
            "last_run": t["last_run"],
            "next_run": t["last_run"] + t["interval"] if t["last_run"] else None,
            "overdue": current_time - t["last_run"] > t["interval"] if t["last_run"] else True,
        }
        for t in _registered_tasks
    ]
