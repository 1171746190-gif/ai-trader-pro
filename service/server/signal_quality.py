import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ==================== Quality Weights ====================

WEIGHTS = {
    "content_length": 0.2,
    "has_symbols": 0.2,
    "has_analysis": 0.25,
    "has_price_target": 0.15,
    "has_risk_management": 0.1,
    "has_timeframe": 0.1,
}

ANALYSIS_KEYWORDS = [
    "support", "resistance", "trend", "momentum", "volume",
    "moving average", "rsi", "macd", "fibonacci", "breakout",
    "consolidation", "divergence", "overbought", "oversold",
    "pattern", "channel", "range", "volatility", "correlation",
    "fundamental", "technical", "indicator", "chart", "level",
    "target", "stop", "entry", "exit", "risk", "reward",
    "bullish", "bearish", "neutral", "long", "short",
    "accumulation", "distribution", "liquidation", "leverage",
    "链上", "支撑位", "阻力位", "趋势", "动量", "成交量",
    "均线", "突破", "盘整", "背离", "超买", "超卖",
]

RISK_KEYWORDS = [
    "stop loss", "take profit", "risk reward", "position size",
    "max loss", "cut loss", "trailing stop", "hedge",
    "止损", "止盈", "仓位", "风险",
]

PRICE_TARGET_PATTERN = re.compile(
    r'\$[\d,]+\.?\d*|\b\d+\.?\d*\s*(USD|USDT|BTC|ETH)\b|\btarget\s+\$?\d+',
    re.IGNORECASE
)

TIMEFRAME_PATTERN = re.compile(
    r'\b(daily|weekly|monthly|hourly|4h|1h|15m|30m|1d|1w|1m|Q[1-4]|quarter|'
    r'短期|中期|长期|日线|周线|月线|小时线|分钟线)\b',
    re.IGNORECASE
)


# ==================== Quality Scoring ====================

def score_content_length(content: str) -> float:
    """Score based on content length."""
    length = len(content)
    if length >= 500:
        return 1.0
    elif length >= 200:
        return 0.7
    elif length >= 100:
        return 0.4
    elif length >= 50:
        return 0.2
    return 0.0


def score_has_symbols(content: str, symbols: Optional[str] = None) -> float:
    """Score based on presence of trading symbols."""
    if symbols:
        return 1.0
    # Check for common symbol patterns
    symbol_pattern = re.compile(r'\b[A-Z]{2,5}\b|\b(BTC|ETH|SOL|BNB|XRP|DOGE|ADA|AVAX|LINK|UNI|AAVE|COMP|SUSHI|CRV|MKR|YFI|SNX|LTC|BCH|ETC|XLM|DOT|MATIC|NEAR|APT|SUI|SEI|TIA|DYM|STRK|ARB|OP|ZKS|POL)\b')
    matches = symbol_pattern.findall(content)
    return min(1.0, len(set(matches)) * 0.3)


def score_has_analysis(content: str) -> float:
    """Score based on technical analysis content."""
    content_lower = content.lower()
    matches = sum(1 for kw in ANALYSIS_KEYWORDS if kw.lower() in content_lower)
    return min(1.0, matches / 5)


def score_has_price_target(content: str) -> float:
    """Score based on price targets."""
    matches = PRICE_TARGET_PATTERN.findall(content)
    return min(1.0, len(matches) * 0.5)


def score_has_risk_management(content: str) -> float:
    """Score based on risk management mentions."""
    content_lower = content.lower()
    matches = sum(1 for kw in RISK_KEYWORDS if kw.lower() in content_lower)
    return min(1.0, matches / 2)


def score_has_timeframe(content: str) -> float:
    """Score based on timeframe mentions."""
    matches = TIMEFRAME_PATTERN.findall(content)
    return 1.0 if matches else 0.0


# ==================== Main Scoring Function ====================

def calculate_quality_score(
    content: str,
    title: str = "",
    symbols: Optional[str] = None,
    signal_type: str = "strategy"
) -> float:
    """Calculate quality score for a signal (0-5 scale)."""
    full_content = f"{title} {content}"
    
    scores = {
        "content_length": score_content_length(content),
        "has_symbols": score_has_symbols(full_content, symbols),
        "has_analysis": score_has_analysis(full_content),
        "has_price_target": score_has_price_target(full_content),
        "has_risk_management": score_has_risk_management(full_content),
        "has_timeframe": score_has_timeframe(full_content),
    }
    
    # Calculate weighted score (0-1)
    weighted = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    
    # Scale to 0-5
    final_score = round(weighted * 5, 2)
    
    logger.debug(
        "Quality score: %.2f (components: %s)",
        final_score, scores
    )
    
    return final_score


def get_quality_breakdown(
    content: str,
    title: str = "",
    symbols: Optional[str] = None
) -> Dict[str, Any]:
    """Get detailed quality score breakdown."""
    full_content = f"{title} {content}"
    
    return {
        "total_score": calculate_quality_score(content, title, symbols),
        "components": {
            "content_length": {
                "score": score_content_length(content),
                "weight": WEIGHTS["content_length"],
                "weighted": score_content_length(content) * WEIGHTS["content_length"],
            },
            "has_symbols": {
                "score": score_has_symbols(full_content, symbols),
                "weight": WEIGHTS["has_symbols"],
                "weighted": score_has_symbols(full_content, symbols) * WEIGHTS["has_symbols"],
            },
            "has_analysis": {
                "score": score_has_analysis(full_content),
                "weight": WEIGHTS["has_analysis"],
                "weighted": score_has_analysis(full_content) * WEIGHTS["has_analysis"],
            },
            "has_price_target": {
                "score": score_has_price_target(full_content),
                "weight": WEIGHTS["has_price_target"],
                "weighted": score_has_price_target(full_content) * WEIGHTS["has_price_target"],
            },
            "has_risk_management": {
                "score": score_has_risk_management(full_content),
                "weight": WEIGHTS["has_risk_management"],
                "weighted": score_has_risk_management(full_content) * WEIGHTS["has_risk_management"],
            },
            "has_timeframe": {
                "score": score_has_timeframe(full_content),
                "weight": WEIGHTS["has_timeframe"],
                "weighted": score_has_timeframe(full_content) * WEIGHTS["has_timeframe"],
            },
        }
    }
