import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ==================== Team Matching ====================

def match_teams(
    participants: List[Dict[str, Any]],
    team_size: int = 3,
    strategy: str = "balanced"
) -> List[List[Dict[str, Any]]]:
    """Match participants into balanced teams.
    
    Args:
        participants: List of participant dicts with skills/experience
        team_size: Desired team size
        strategy: Matching strategy (random, balanced, skill_based)
    
    Returns:
        List of teams (each team is a list of participants)
    """
    if not participants:
        return []
    
    import random
    
    if strategy == "random":
        random.shuffle(participants)
    elif strategy == "balanced":
        # Sort by skill level and distribute evenly
        participants.sort(key=lambda p: p.get("skill_rating", 0), reverse=True)
    
    teams = []
    current_team = []
    
    for participant in participants:
        current_team.append(participant)
        if len(current_team) >= team_size:
            teams.append(current_team)
            current_team = []
    
    # Add remaining participants to last team
    if current_team:
        if teams and len(current_team) < team_size // 2:
            # Distribute to existing teams
            for i, member in enumerate(current_team):
                teams[i % len(teams)].append(member)
        else:
            teams.append(current_team)
    
    return teams


def calculate_team_compatibility(
    team: List[Dict[str, Any]]
) -> float:
    """Calculate team compatibility score.
    
    Returns score 0-1 based on skill diversity and balance.
    """
    if not team or len(team) < 2:
        return 1.0
    
    skill_levels = [p.get("skill_rating", 50) for p in team]
    avg_skill = sum(skill_levels) / len(skill_levels)
    
    # Calculate variance (lower is more balanced)
    variance = sum((s - avg_skill) ** 2 for s in skill_levels) / len(skill_levels)
    max_variance = 2500  # (100-0)^2 / 4
    
    balance_score = 1 - (variance / max_variance)
    
    # Diversity bonus for different specializations
    specializations = set()
    for p in team:
        specs = p.get("specializations", [])
        specializations.update(specs)
    
    diversity_score = min(1.0, len(specializations) / len(team))
    
    return balance_score * 0.6 + diversity_score * 0.4


def suggest_team_name(
    team_members: List[Dict[str, Any]]
) -> str:
    """Generate a team name based on member characteristics."""
    prefixes = ["Alpha", "Beta", "Gamma", "Delta", "Sigma", "Omega", "Cyber", "Quantum"]
    suffixes = ["Traders", "Wolves", "Hawks", "Bulls", "Bears", "Whales", "Bots", "Quant"]
    
    import random
    prefix = random.choice(prefixes)
    suffix = random.choice(suffixes)
    
    return f"{prefix}{suffix}"
