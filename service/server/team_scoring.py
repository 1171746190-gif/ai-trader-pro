import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ==================== Team Scoring ====================

def calculate_team_score(
    trades: List[Dict[str, Any]],
    metric: str = "return"
) -> Dict[str, Any]:
    """Calculate aggregate score for a team.
    
    Args:
        trades: List of trade dicts from all team members
        metric: Scoring metric
    
    Returns:
        Dict with score breakdown
    """
    if not trades:
        return {"total_score": 0, "metrics": {}}
    
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    total_trades = len(trades)
    
    winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
    
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
    
    # Calculate max drawdown
    cumulative = 0
    peak = 0
    max_dd = 0
    for trade in trades:
        cumulative += trade.get("pnl", 0)
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    # Risk-adjusted return
    risk_adjusted = total_pnl / (max_dd + 1) if max_dd > 0 else total_pnl
    
    return {
        "total_score": total_pnl,
        "metrics": {
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 4),
            "avg_pnl_per_trade": round(avg_pnl, 4),
            "max_drawdown": round(max_dd, 4),
            "risk_adjusted_return": round(risk_adjusted, 4),
        }
    }


def rank_teams(
    teams: List[Dict[str, Any]],
    metric: str = "return"
) -> List[Dict[str, Any]]:
    """Rank teams by specified metric.
    
    Args:
        teams: List of team dicts with score data
        metric: Ranking metric
    
    Returns:
        Sorted list of teams with rank
    """
    if metric == "return":
        key = lambda t: t.get("total_score", 0)
    elif metric == "win_rate":
        key = lambda t: t.get("metrics", {}).get("win_rate", 0)
    elif metric == "risk_adjusted":
        key = lambda t: t.get("metrics", {}).get("risk_adjusted_return", 0)
    else:
        key = lambda t: t.get("total_score", 0)
    
    sorted_teams = sorted(teams, key=key, reverse=True)
    
    for i, team in enumerate(sorted_teams):
        team["rank"] = i + 1
    
    return sorted_teams


def calculate_collaboration_bonus(
    team_members: List[Dict[str, Any]]
) -> float:
    """Calculate bonus for team collaboration.
    
    Returns multiplier based on member interaction.
    """
    if len(team_members) < 2:
        return 1.0
    
    # Count cross-member signals (signals that influenced other members)
    cross_signals = 0
    for member in team_members:
        cross_signals += member.get("signals_shared", 0)
    
    # Bonus increases with more collaboration
    bonus = 1.0 + min(0.2, cross_signals * 0.01)
    
    return round(bonus, 4)
