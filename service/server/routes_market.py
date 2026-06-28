from typing import Optional

from fastapi import FastAPI, Header

from market_intel import (
    get_market_overview,
    get_financial_news,
    get_macro_signals,
    get_etf_flows,
    get_featured_stocks,
    get_stock_latest,
    get_stock_history,
)


def register_routes(app: FastAPI):
    """Register market intelligence routes."""
    
    @app.get("/api/market-intel/overview")
    async def market_overview():
        """Get market overview."""
        return get_market_overview()
    
    @app.get("/api/market-intel/news")
    async def financial_news(
        limit: int = 12,
        offset: int = 0,
    ):
        """Get financial news."""
        return get_financial_news(limit=limit, offset=offset)
    
    @app.get("/api/market-intel/macro-signals")
    async def macro_signals():
        """Get macro signals."""
        return get_macro_signals()
    
    @app.get("/api/market-intel/etf-flows")
    async def etf_flows():
        """Get ETF flow data."""
        return get_etf_flows()
    
    @app.get("/api/market-intel/stocks/featured")
    async def featured_stocks(
        limit: int = 10,
    ):
        """Get featured stocks."""
        return get_featured_stocks(limit=limit)
    
    @app.get("/api/market-intel/stocks/{symbol}/latest")
    async def stock_latest(symbol: str):
        """Get latest data for a stock."""
        return get_stock_latest(symbol)
    
    @app.get("/api/market-intel/stocks/{symbol}/history")
    async def stock_history(
        symbol: str,
        limit: int = 30,
    ):
        """Get historical data for a stock."""
        return get_stock_history(symbol, limit=limit)
