import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ==================== Scoring Constants ====================

DRAWDOWN_PENALTY_MULTIPLIER = 3.0
RISK_FREE_RATE = 0.02  # 2% annual risk-free rate


# ==================== Profit Score ====================

def calculate_profit_score(profit_pct: float, drawdown_pct: float = 0) -> float:
    """Calculate profit score with drawdown penalty."""
    if profit_pct <= 0:
        return profit_pct
    
    drawdown_penalty = 1 - (drawdown_pct * DRAWDOWN_PENALTY_MULTIPLIER)
    drawdown_penalty = max(0.1, drawdown_penalty)  # Minimum 10% weight
    
    return profit_pct * drawdown_penalty


# ==================== Sharpe Ratio ====================

def calculate_sharpe_ratio(returns: List[float]) -> float:
    """Calculate annualized Sharpe ratio."""
    if len(returns) < 2:
        return 0.0
    
    avg_return = sum(returns) / len(returns)
    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)
    
    if std_dev == 0:
        return 0.0
    
    # Annualize (assuming daily returns)
    return ((avg_return - RISK_FREE_RATE / 252) / std_dev) * math.sqrt(252)


# ==================== Win Rate ====================

def calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
    """Calculate win rate from trades."""
    if not trades:
        return 0.0
    
    winning_trades = sum(1 for t in trades if t.get("profit", 0) > 0)
    return winning_trades / len(trades)


# ==================== Max Drawdown ====================

def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """Calculate maximum drawdown from equity curve."""
    if not equity_curve:
        return 0.0
    
    max_dd = 0.0
    peak = equity_curve[0]
    
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    return max_dd


# ==================== Composite Score ====================

def calculate_composite_score(
    profit_pct: float,
    drawdown_pct: float,
    sharpe: float,
    win_rate: float,
    trade_count: int,
) -> float:
    """Calculate composite trading score."""
    # Profit component (40%)
    profit_score = min(profit_pct / 100, 1.0) * 0.4
    
    # Risk-adjusted component (30%)
    risk_score = min(sharpe / 3, 1.0) * 0.3
    
    # Consistency component (20%)
    consistency_score = win_rate * 0.2
    
    # Activity component (10%)
    activity_score = min(trade_count / 50, 1.0) * 0.1
    
    total = profit_score + risk_score + consistency_score + activity_score
    
    # Drawdown penalty
    dd_penalty = max(0, 1 - drawdown_pct * 2)
    
    return total * dd_penalty


# ==================== Leaderboard Ranking ====================

def rank_participants(
    participants: List[Dict[str, Any]],
    metric: str = "return"
) -> List[Dict[str, Any]]:
    """Rank participants by specified metric."""
    if metric == "return":
        key = lambda p: p.get("total_return", 0)
    elif metric == "drawdown":
        key = lambda p: p.get("max_drawdown", float('inf'))
    elif metric == "sharpe":
        key = lambda p: p.get("sharpe_ratio", 0)
    elif metric == "risk":
        key = lambda p: p.get("risk_adjusted_return", 0)
    elif metric == "quality":
        key = lambda p: p.get("signal_quality", 0)
    else:
        key = lambda p: p.get("total_return", 0)
    
    reverse = metric != "drawdown"
    ranked = sorted(participants, key=key, reverse=reverse)
    
    for i, p in enumerate(ranked):
        p["rank"] = i + 1
    
    return ranked
