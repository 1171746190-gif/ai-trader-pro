import json
import math
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request

# ==================== Constants ====================

OPERATION_TYPES = {"buy", "sell", "short", "cover"}
MARKET_TYPES = {"us-stock", "crypto", "polymarket", "forex", "options", "futures"}

# ==================== Auth Helpers ====================

def extract_token(authorization: Optional[str]) -> str:
    """Extract token from Authorization header."""
    if not authorization:
        return ""
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


def get_current_agent(authorization: Optional[str]) -> Dict[str, Any]:
    """Get current agent from authorization token."""
    from services import _get_agent_by_token
    token = extract_token(authorization)
    agent = _get_agent_by_token(token)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return agent


# ==================== Request Parsing ====================

def parse_executed_at(executed_at: str) -> str:
    """Parse executed_at parameter."""
    if executed_at.lower() == "now":
        return datetime.now(timezone.utc).isoformat()
    return executed_at


def parse_symbols(symbols: Optional[str]) -> Optional[str]:
    """Parse and validate symbols string."""
    if not symbols:
        return None
    # Normalize: uppercase, remove spaces
    symbols = symbols.upper().replace(" ", "")
    return symbols


def parse_tags(tags: Optional[str]) -> Optional[str]:
    """Parse and validate tags string."""
    if not tags:
        return None
    tags = tags.lower().replace(" ", "")
    return tags


# ==================== Validation ====================

def validate_market(market: str) -> str:
    """Validate market type."""
    market = market.lower().strip()
    if market not in MARKET_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid market '{market}'. Must be one of: {', '.join(MARKET_TYPES)}"
        )
    return market


def validate_operation(action: str) -> str:
    """Validate operation type."""
    action = action.lower().strip()
    if action not in OPERATION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{action}'. Must be one of: {', '.join(OPERATION_TYPES)}"
        )
    return action


def validate_trade_params(
    price: float,
    quantity: float,
    market: str = "crypto"
) -> None:
    """Validate trade parameters."""
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    if quantity > 1_000_000:
        raise HTTPException(status_code=400, detail="Quantity exceeds maximum (1,000,000)")
    
    if price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")
    if price > 10_000_000:
        raise HTTPException(status_code=400, detail="Price exceeds maximum ($10M)")
    
    trade_value = price * quantity
    if trade_value > 1_000_000_000:
        raise HTTPException(status_code=400, detail="Trade value exceeds maximum ($1B)")


# ==================== Market Time Check ====================

def check_market_hours(market: str) -> None:
    """Check if market is open for trading."""
    from utils import is_us_market_open, get_next_market_open
    
    if market == "us-stock":
        if not is_us_market_open():
            next_open = get_next_market_open()
            raise HTTPException(
                status_code=400,
                detail=f"US stock market is closed. Next open: {next_open}"
            )


# ==================== Fund Check ====================

def check_sufficient_funds(
    agent_id: int,
    market: str,
    action: str,
    price: float,
    quantity: float,
    cursor=None
) -> None:
    """Check if agent has sufficient funds for trade."""
    from fees import calculate_fee
    
    own_connection = False
    if cursor is None:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        own_connection = True
    
    trade_value = price * quantity
    fee = calculate_fee(trade_value)
    
    if action.lower() in ("buy", "short"):
        # Need enough funds for trade + fee
        cursor.execute("SELECT cash_balance FROM agents WHERE id = ?", (agent_id,))
        row = cursor.fetchone()
        
        if not row:
            if own_connection:
                conn.close()
            raise HTTPException(status_code=400, detail="Agent not found")
        
        balance = row[0] if row else 0
        required = trade_value + fee
        
        if balance < required:
            if own_connection:
                conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient funds. Balance: ${balance:.2f}, Required: ${required:.2f}"
            )
    
    # For sell/cover, check position
    if action.lower() == "sell":
        cursor.execute(
            "SELECT quantity FROM positions WHERE agent_id = ? AND symbol = ?",
            (agent_id, market)
        )
        row = cursor.fetchone()
        if not row or row[0] < quantity:
            if own_connection:
                conn.close()
            raise HTTPException(status_code=400, detail="Insufficient position to sell")
    
    if action.lower() == "cover":
        cursor.execute(
            "SELECT quantity FROM positions WHERE agent_id = ? AND symbol = ?",
            (agent_id, market)
        )
        row = cursor.fetchone()
        if not row or abs(row[0]) < quantity:
            if own_connection:
                conn.close()
            raise HTTPException(status_code=400, detail="Insufficient short position to cover")
    
    if own_connection:
        conn.close()


# ==================== Position Check ====================

def check_position_for_action(
    agent_id: int,
    symbol: str,
    market: str,
    action: str,
    quantity: float,
    cursor=None
) -> bool:
    """Check if agent has valid position for action."""
    own_connection = False
    if cursor is None:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        own_connection = True
    
    cursor.execute(
        "SELECT quantity, side FROM positions WHERE agent_id = ? AND symbol = ? AND market = ?",
        (agent_id, symbol, market)
    )
    row = cursor.fetchone()
    
    has_position = False
    if action.lower() in ("sell", "cover"):
        if not row:
            has_position = False
        elif action.lower() == "sell" and row["side"] == "long" and row["quantity"] >= quantity:
            has_position = True
        elif action.lower() == "cover" and row["side"] == "short" and abs(row["quantity"]) >= quantity:
            has_position = True
    else:
        has_position = True  # buy/short always allowed (fund check separate)
    
    if own_connection:
        conn.close()
    
    return has_position


# ==================== API Access Log ====================

def api_access_log_enabled() -> bool:
    """Check if API access logging is enabled."""
    return os.getenv("API_STDERR_LOG", "false").lower() in ("1", "true", "yes", "on")


# ==================== Signal Formatting ====================

def format_signal_response(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Format signal for API response."""
    return {
        "id": signal.get("id"),
        "agent_id": signal.get("agent_id"),
        "agent_name": signal.get("agent_name"),
        "message_type": signal.get("message_type"),
        "market": signal.get("market"),
        "title": signal.get("title"),
        "content": signal.get("content"),
        "symbol": signal.get("symbol"),
        "action": signal.get("action"),
        "price": signal.get("price"),
        "quantity": signal.get("quantity"),
        "side": signal.get("side"),
        "symbols": signal.get("symbols"),
        "tags": signal.get("tags"),
        "challenge_key": signal.get("challenge_key"),
        "quality_score": signal.get("quality_score"),
        "points_earned": signal.get("points_earned"),
        "created_at": signal.get("created_at"),
    }


def format_agent_response(agent: Dict[str, Any]) -> Dict[str, Any]:
    """Format agent for API response (without sensitive data)."""
    return {
        "id": agent.get("id"),
        "name": agent.get("name"),
        "email": agent.get("email"),
        "identity_status": agent.get("identity_status"),
        "is_verified": agent.get("is_verified"),
        "initial_balance": agent.get("initial_balance"),
        "cash_balance": agent.get("cash_balance"),
        "points": agent.get("points"),
        "created_at": agent.get("created_at"),
    }
