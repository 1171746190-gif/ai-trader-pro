import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ==================== Market Overview ====================

def get_market_overview() -> Dict[str, Any]:
    """Get overall market overview."""
    try:
        # Get major indices from Alpha Vantage
        indices = ["SPY", "QQQ", "DIA", "IWM"]
        index_data = {}
        
        from config import get_config
        api_key = get_config().get("alpha_vantage_api_key", "demo")
        
        for symbol in indices:
            try:
                url = "https://www.alphavantage.co/query"
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": api_key,
                }
                response = requests.get(url, params=params, timeout=5)
                data = response.json()
                
                if "Global Quote" in data:
                    quote = data["Global Quote"]
                    index_data[symbol] = {
                        "price": float(quote.get("05. price", 0)),
                        "change": float(quote.get("09. change", 0)),
                        "change_percent": quote.get("10. change percent", "0%"),
                    }
            except Exception as e:
                logger.warning("Failed to get %s: %s", symbol, e)
        
        # Get crypto overview
        crypto_data = {}
        try:
            url = "https://api.hyperliquid.xyz/info"
            response = requests.post(url, json={"type": "allMids"}, timeout=5)
            data = response.json()
            
            for symbol in ["BTC", "ETH", "SOL"]:
                if symbol in data:
                    crypto_data[symbol] = {
                        "price": float(data[symbol]),
                        "change_24h": None,  # Would need additional API call
                    }
        except Exception as e:
            logger.warning("Failed to get crypto data: %s", e)
        
        return {
            "indices": index_data,
            "crypto": crypto_data,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error("Market overview failed: %s", e)
        return {"indices": {}, "crypto": {}, "error": str(e)}


# ==================== Financial News ====================

def get_financial_news(limit: int = 12, offset: int = 0) -> List[Dict[str, Any]]:
    """Get financial news."""
    try:
        from config import get_config
        api_key = get_config().get("alpha_vantage_api_key", "demo")
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": api_key,
            "limit": min(limit, 50),
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "feed" in data:
            news = []
            for item in data["feed"][offset:offset+limit]:
                news.append({
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "url": item.get("url"),
                    "source": item.get("source"),
                    "published_at": item.get("time_published"),
                    "sentiment": item.get("overall_sentiment_score"),
                    "tickers": [t.get("ticker") for t in item.get("ticker_sentiment", [])],
                })
            return news
        
        return []
    except Exception as e:
        logger.error("News fetch failed: %s", e)
        return []


# ==================== Macro Signals ====================

def get_macro_signals() -> Dict[str, Any]:
    """Get macro economic signals."""
    try:
        signals = {
            "fed_policy": "neutral",  # Would come from Fed data API
            "inflation_trend": "stable",
            "gdp_growth": "moderate",
            "unemployment": "low",
            "yield_curve": "normal",
            "dollar_strength": "moderate",
            "credit_spreads": "tight",
            "volatility_index": None,
        }
        
        # Try to get VIX
        try:
            from price_fetcher import get_alpha_vantage_price
            vix_price = get_alpha_vantage_price("VIX", api_key="demo")
            if vix_price:
                signals["volatility_index"] = vix_price
        except Exception:
            pass
        
        return signals
    except Exception as e:
        logger.error("Macro signals failed: %s", e)
        return {}


# ==================== ETF Flows ====================

def get_etf_flows() -> Dict[str, Any]:
    """Get ETF flow data."""
    # This would typically come from a paid data provider
    # Returning mock data for demonstration
    return {
        "spy": {"inflow": 1250000000, "outflow": 890000000},
        "qqq": {"inflow": 678000000, "outflow": 234000000},
        "gld": {"inflow": 456000000, "outflow": 123000000},
        "tlt": {"inflow": 234000000, "outflow": 567000000},
        "timestamp": time.time(),
    }


# ==================== Featured Stocks ====================

def get_featured_stocks(limit: int = 10) -> List[Dict[str, Any]]:
    """Get featured/most active stocks."""
    try:
        from config import get_config
        api_key = get_config().get("alpha_vantage_api_key", "demo")
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TOP_GAINERS_LOSERS",
            "apikey": api_key,
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        stocks = []
        
        if "top_gainers" in data:
            for item in data["top_gainers"][:limit//2]:
                stocks.append({
                    "symbol": item.get("ticker"),
                    "name": item.get("ticker"),
                    "price": float(item.get("price", 0)),
                    "change_percent": item.get("change_percentage"),
                    "direction": "up",
                })
        
        if "top_losers" in data:
            for item in data["top_losers"][:limit//2]:
                stocks.append({
                    "symbol": item.get("ticker"),
                    "name": item.get("ticker"),
                    "price": float(item.get("price", 0)),
                    "change_percent": item.get("change_percentage"),
                    "direction": "down",
                })
        
        return stocks[:limit]
    except Exception as e:
        logger.error("Featured stocks fetch failed: %s", e)
        return []


# ==================== Stock Details ====================

def get_stock_latest(symbol: str) -> Dict[str, Any]:
    """Get latest data for a specific stock."""
    try:
        from config import get_config
        from price_fetcher import get_alpha_vantage_price
        
        api_key = get_config().get("alpha_vantage_api_key", "demo")
        price = get_alpha_vantage_price(symbol, api_key)
        
        if price:
            return {
                "symbol": symbol,
                "price": price,
                "timestamp": time.time(),
            }
        
        return {"symbol": symbol, "error": "Price not available"}
    except Exception as e:
        logger.error("Stock latest failed for %s: %s", symbol, e)
        return {"symbol": symbol, "error": str(e)}


def get_stock_history(symbol: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Get historical data for a specific stock."""
    try:
        from config import get_config
        api_key = get_config().get("alpha_vantage_api_key", "demo")
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": api_key,
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        history = []
        if "Time Series (Daily)" in data:
            for date, values in list(data["Time Series (Daily)"].items())[:limit]:
                history.append({
                    "date": date,
                    "open": float(values.get("1. open", 0)),
                    "high": float(values.get("2. high", 0)),
                    "low": float(values.get("3. low", 0)),
                    "close": float(values.get("4. close", 0)),
                    "volume": int(values.get("5. volume", 0)),
                })
        
        return history
    except Exception as e:
        logger.error("Stock history failed for %s: %s", symbol, e)
        return []


# ==================== Refresh ====================

def refresh_market_data() -> Dict[str, Any]:
    """Refresh all market intelligence data."""
    import time
    
    results = {
        "overview": False,
        "news": False,
        "macro": False,
        "etf_flows": False,
    }
    
    try:
        get_market_overview()
        results["overview"] = True
    except Exception as e:
        logger.error("Overview refresh failed: %s", e)
    
    try:
        get_financial_news(limit=5)
        results["news"] = True
    except Exception as e:
        logger.error("News refresh failed: %s", e)
    
    try:
        get_macro_signals()
        results["macro"] = True
    except Exception as e:
        logger.error("Macro refresh failed: %s", e)
    
    try:
        get_etf_flows()
        results["etf_flows"] = True
    except Exception as e:
        logger.error("ETF flows refresh failed: %s", e)
    
    return results


# ==================== Adanos Sentiment (Optional) ====================

def get_adanos_sentiment(query: str = "crypto") -> Optional[Dict[str, Any]]:
    """Get sentiment analysis from Adanos API."""
    try:
        from config import get_config
        api_key = get_config().get("adanos_api_key")
        
        if not api_key:
            return None
        
        url = "https://api.adanos.org/v1/sentiment"
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"q": query}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        return response.json()
    except Exception as e:
        logger.error("Adanos sentiment failed: %s", e)
        return None
