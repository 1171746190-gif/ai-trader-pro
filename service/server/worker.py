#!/usr/bin/env python3
"""
AI-Trader Pro Background Worker

Runs background tasks independently from the API server.
Usage: python worker.py
"""

import logging
import os
import signal
import sys
import time

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "worker.log")),
        logging.StreamHandler(sys.stderr),
    ]
)

logger = logging.getLogger(__name__)

# ==================== Graceful Shutdown ====================

_shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _shutdown_requested
    logger.info("Shutdown signal received (%s), finishing current tasks...", signum)
    _shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ==================== Single Instance Lock ====================

def acquire_lock() -> bool:
    """Acquire single instance lock."""
    lock_file = os.path.join(os.path.dirname(__file__), ".worker.lock")
    try:
        import fcntl
        fd = open(lock_file, "w")
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (ImportError, IOError, OSError):
        # Windows or lock already held
        if os.path.exists(lock_file):
            pid = open(lock_file).read().strip()
            if pid and pid != str(os.getpid()):
                try:
                    os.kill(int(pid), 0)
                    logger.warning("Worker already running (PID: %s)", pid)
                    return False
                except (OSError, ValueError):
                    pass
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
        return True


# ==================== Worker Loop ====================

def run_worker():
    """Main worker loop."""
    if not acquire_lock():
        logger.error("Another worker instance is already running")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("AI-Trader Pro Background Worker Started")
    logger.info("PID: %s", os.getpid())
    logger.info("=" * 60)
    
    # Import tasks
    from tasks import run_pending_tasks, get_task_status
    
    iteration = 0
    while not _shutdown_requested:
        try:
            iteration += 1
            if iteration % 60 == 0:  # Log status every 60 iterations
                status = get_task_status()
                for task in status:
                    logger.info(
                        "Task: %s | Interval: %ds | Last run: %.0fs ago",
                        task["name"], task["interval"],
                        time.time() - task.get("last_run", 0) if task.get("last_run") else -1
                    )
            
            run_pending_tasks()
            time.sleep(1)
            
        except Exception as e:
            logger.error("Worker loop error: %s", e)
            time.sleep(5)
    
    logger.info("Worker shutting down gracefully")


# ==================== Main ====================

if __name__ == "__main__":
    run_worker()
