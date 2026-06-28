"""Experiment metrics calculation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from database import get_db_connection

logger = logging.getLogger(__name__)


def get_metrics(experiment_key: str) -> Dict[str, Any]:
    """Calculate metrics for an experiment.
    
    Returns participation, engagement, and outcome metrics.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get variant assignments
    cursor.execute("""
        SELECT variant_key, COUNT(*) as count
        FROM experiment_assignments
        WHERE experiment_key = ?
        GROUP BY variant_key
    """, (experiment_key,))
    
    variant_counts = {row["variant_key"]: row["count"] for row in cursor.fetchall()}
    
    # Get signal counts per variant
    cursor.execute("""
        SELECT 
            ea.variant_key,
            s.message_type,
            COUNT(*) as signal_count
        FROM signals s
        JOIN experiment_assignments ea ON s.agent_id = ea.agent_id
        WHERE ea.experiment_key = ?
        GROUP BY ea.variant_key, s.message_type
    """, (experiment_key,))
    
    signal_counts = {}
    for row in cursor.fetchall():
        variant = row["variant_key"]
        msg_type = row["message_type"]
        if variant not in signal_counts:
            signal_counts[variant] = {}
        signal_counts[variant][msg_type] = row["signal_count"]
    
    # Get quality scores per variant
    cursor.execute("""
        SELECT 
            ea.variant_key,
            AVG(s.quality_score) as avg_quality,
            COUNT(*) as total_signals
        FROM signals s
        JOIN experiment_assignments ea ON s.agent_id = ea.agent_id
        WHERE ea.experiment_key = ? AND s.quality_score IS NOT NULL
        GROUP BY ea.variant_key
    """, (experiment_key,))
    
    quality_scores = {}
    for row in cursor.fetchall():
        quality_scores[row["variant_key"]] = {
            "avg_quality": row["avg_quality"],
            "total_signals": row["total_signals"],
        }
    
    conn.close()
    
    # Calculate engagement rate
    metrics = {
        "experiment_key": experiment_key,
        "participation": variant_counts,
        "signals": signal_counts,
        "quality": quality_scores,
    }
    
    # Calculate engagement rate (signals per agent)
    for variant, count in variant_counts.items():
        total_signals = sum(signal_counts.get(variant, {}).values())
        metrics["signals"][variant]["engagement_rate"] = (
            total_signals / count if count > 0 else 0
        )
    
    return metrics


def compare_variants(experiment_key: str) -> Dict[str, Any]:
    """Compare performance between experiment variants."""
    metrics = get_metrics(experiment_key)
    
    variants = list(metrics["participation"].keys())
    if len(variants) < 2:
        return {"error": "Need at least 2 variants for comparison"}
    
    comparison = {
        "experiment_key": experiment_key,
        "variants": {},
        "winner": None,
    }
    
    best_variant = None
    best_score = -1
    
    for variant in variants:
        quality_data = metrics["quality"].get(variant, {})
        avg_quality = quality_data.get("avg_quality", 0) or 0
        engagement = metrics["signals"].get(variant, {}).get("engagement_rate", 0)
        
        # Composite score: quality * engagement
        score = avg_quality * engagement
        
        comparison["variants"][variant] = {
            "participants": metrics["participation"].get(variant, 0),
            "avg_quality": avg_quality,
            "engagement_rate": engagement,
            "composite_score": score,
        }
        
        if score > best_score:
            best_score = score
            best_variant = variant
    
    comparison["winner"] = best_variant
    
    return comparison
