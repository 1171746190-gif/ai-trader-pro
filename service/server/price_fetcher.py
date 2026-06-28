import logging
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ==================== Cache ====================

_price_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 60  # seconds


def _get_cached_price(key: str) -> Optional[float]:
    """Get cached price if not expired."""
    if key in _price_cache:
        entry = _price_cache[key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["price"]
    return None


def _set_cached_price(key: str, price: float) -> None:
    """Cache a price."""
    _price_cache[key] = {"price": price, "timestamp": time.time()}


# ==================== Alpha Vantage (US Stocks) ====================

def get_alpha_vantage_price(symbol: str, api_key: Optional[str] = None) -> Optional[float]:
    """Get stock price from Alpha Vantage."""
    cache_key = f"av:{symbol}"
    cached = _get_cached_price(cache_key)
    if cached is not None:
        return cached
    
    if not api_key:
        from config import get_config
        api_key = get_config().get("alpha_vantage_api_key", "demo")
    
    try:
        url = f"https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": api_key,
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "Global Quote" in data and "05. price" in data["Global Quote"]:
            price = float(data["Global Quote"]["05. price"])
            _set_cached_price(cache_key, price)
            return price
        
        logger.warning("Alpha Vantage response missing price for %s: %s", symbol, data)
        return None
    except Exception as e:
        logger.error("Alpha Vantage fetch failed for %s: %s", symbol, e)
        return None


def get_alpha_vantage_batch(symbols: List[str], api_key: Optional[str] = None) -> Dict[str, float]:
    """Get prices for multiple symbols from Alpha Vantage."""
    if not api_key:
        from config import get_config
        api_key = get_config().get("alpha_vantage_api_key", "demo")
    
    results = {}
    for symbol in symbols:
        price = get_alpha_vantage_price(symbol, api_key)
        if price:
            results[symbol] = price
        time.sleep(0.2)  # Rate limiting
    
    return results


# ==================== HyperLiquid (Crypto) ====================

def get_hyperliquid_price(symbol: str) -> Optional[float]:
    """Get crypto price from HyperLiquid."""
    cache_key = f"hl:{symbol}"
    cached = _get_cached_price(cache_key)
    if cached is not None:
        return cached
    
    try:
        url = "https://api.hyperliquid.xyz/info"
        payload = {"type": "allMids"}
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        # Find the symbol in the response
        symbol_upper = symbol.upper()
        if isinstance(data, dict) and symbol_upper in data:
            price = float(data[symbol_upper])
            _set_cached_price(cache_key, price)
            return price
        
        logger.warning("HyperLiquid response missing %s", symbol)
        return None
    except Exception as e:
        logger.error("HyperLiquid fetch failed for %s: %s", symbol, e)
        return None


def get_hyperliquid_prices(symbols: List[str]) -> Dict[str, float]:
    """Get prices for multiple crypto symbols from HyperLiquid."""
    try:
        url = "https://api.hyperliquid.xyz/info"
        payload = {"type": "allMids"}
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        results = {}
        if isinstance(data, dict):
            for symbol in symbols:
                symbol_upper = symbol.upper()
                if symbol_upper in data:
                    price = float(data[symbol_upper])
                    results[symbol] = price
                    _set_cached_price(f"hl:{symbol}", price)
        
        return results
    except Exception as e:
        logger.error("HyperLiquid batch fetch failed: %s", e)
        return {}


# ==================== Polymarket ====================

def get_polymarket_price(token_id: str) -> Optional[float]:
    """Get prediction market price from Polymarket."""
    cache_key = f"pm:{token_id}"
    cached = _get_cached_price(cache_key)
    if cached is not None:
        return cached
    
    try:
        url = f"https://gamma-api.polymarket.com/markets/{token_id}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "outcomePrices" in data:
            # Parse outcome prices
            prices = data["outcomePrices"]
            if isinstance(prices, list) and len(prices) > 0:
                price = float(prices[0]) * 100  # Convert to percentage
                _set_cached_price(cache_key, price)
                return price
        
        logger.warning("Polymarket response missing price for %s", token_id)
        return None
    except Exception as e:
        logger.error("Polymarket fetch failed for %s: %s", token_id, e)
        return None


# ==================== yfinance (Fallback) ====================

def get_yfinance_price(symbol: str) -> Optional[float]:
    """Get price from yfinance as fallback."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if "regularMarketPrice" in info:
            return float(info["regularMarketPrice"])
        # Try historical data
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None
    except ImportError:
        logger.warning("yfinance not installed")
        return None
    except Exception as e:
        logger.error("yfinance fetch failed for %s: %s", symbol, e)
        return None


# ==================== Universal Price Getter ====================

def get_price(symbol: str, market: str = "crypto") -> Optional[float]:
    """Get price for any symbol across any market."""
    market = market.lower()
    
    if market == "crypto":
        price = get_hyperliquid_price(symbol)
        if price is None:
            price = get_yfinance_price(f"{symbol}-USD")
        return price
    
    elif market == "us-stock":
        price = get_alpha_vantage_price(symbol)
        if price is None:
            price = get_yfinance_price(symbol)
        return price
    
    elif market == "polymarket":
        return get_polymarket_price(symbol)
    
    else:
        # Try all sources
        for getter in [get_alpha_vantage_price, get_hyperliquid_price, get_yfinance_price]:
            price = getter(symbol)
            if price is not None:
                return price
        return None


def get_prices(symbols: List[str], market: str = "crypto") -> Dict[str, float]:
    """Get prices for multiple symbols."""
    results = {}
    for symbol in symbols:
        price = get_price(symbol, market)
        if price is not None:
            results[symbol] = price
    return results


# ==================== Position Price Update ====================

def update_all_prices() -> Dict[str, Any]:
    """Update prices for all open positions."""
    from database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all unique symbols from positions
    cursor.execute("SELECT DISTINCT symbol, market FROM positions")
    rows = cursor.fetchall()
    
    updated = 0
    failed = 0
    
    for row in rows:
        symbol = row["symbol"]
        market = row["market"]
        
        price = get_price(symbol, market)
        if price is not None:
            # Update position with current price
            cursor.execute(
                "UPDATE positions SET current_price = ? WHERE symbol = ? AND market = ?",
                (price, symbol, market)
            )
            updated += 1
        else:
            failed += 1
    
    conn.commit()
    conn.close()
    
    result = {"updated": updated, "failed": failed, "total": updated + failed}
    logger.info("Price update completed: %s", result)
    return result


def get_price_source_status() -> Dict[str, Any]:
    """Get status of all price sources."""
    return {
        "alpha_vantage": _test_source("https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo"),
        "hyperliquid": _test_source("https://api.hyperliquid.xyz/info", method="POST", json={"type": "allMids"}),
        "polymarket": _test_source("https://gamma-api.polymarket.com/markets"),
    }


def _test_source(url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
    """Test if a price source is available."""
    try:
        if method == "POST":
            response = requests.post(url, timeout=5, **kwargs)
        else:
            response = requests.get(url, timeout=5, **kwargs)
        return {
            "available": response.status_code == 200,
            "status_code": response.status_code,
            "latency_ms": int(response.elapsed.total_seconds() * 1000),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
