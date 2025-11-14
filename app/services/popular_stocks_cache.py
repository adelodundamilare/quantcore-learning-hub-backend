import asyncio
import time
from typing import Dict, Optional, List
from datetime import datetime
import logging

from app.services.polygon import polygon_service

logger = logging.getLogger(__name__)

class PopularStocksCache:
    def __init__(self):
        self.cache: Dict[str, dict] = {}
        self.cache_timestamp: Optional[float] = None
        self.cache_duration = 600  # 10 minutes
        self.refresh_interval = 300  # 5 minutes
        self.is_refreshing = False

        # Popular stocks list
        self.popular_stocks = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX",
            "AMD", "INTC", "CRM", "ORCL", "CSCO", "ADBE", "PYPL", "UBER",
            "SPOT", "ZOOM", "SHOP", "SQ", "COIN", "ROKU", "PINS", "SNAP",
            "TTD", "OKTA", "ZS", "CRWD", "DDOG", "NOW", "DOCU", "PLTR","ETHA",
            "IBIT","SPY","QQQ","IWM"
        ]

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self.cache_timestamp:
            return False
        return time.time() - self.cache_timestamp < self.cache_duration

    def _should_refresh(self) -> bool:
        """Check if we should refresh the cache."""
        if not self.cache_timestamp:
            return True
        return time.time() - self.cache_timestamp > self.refresh_interval

    async def _fetch_popular_stock_data(self, symbol: str) -> dict:
        """Fetch complete data for a single popular stock."""
        try:
            details = await polygon_service.get_stock_details_combined(symbol)

            if details:
                complete_data = {
                    "symbol": symbol,
                    "name": details.get("name", symbol),
                    "price": details.get("price"),
                    "change": details.get("change"),
                    "change_percent": details.get("change_percent"),
                    "high": details.get("high"),
                    "low": details.get("low"),
                    "open": details.get("open"),
                    "volume": details.get("volume"),
                    "avg_volume": details.get("avg_volume"),
                    "market_cap": details.get("market_cap"),
                    "pe_ratio": details.get("pe_ratio"),
                    "description": details.get("description"),
                    "ceo": details.get("ceo"),
                    "employees": details.get("employees"),
                    "headquarters": details.get("headquarters"),
                    "founded": details.get("founded"),
                    "sparkline_data": details.get("sparkline_data"),
                    "logo_url": details.get("logo_url"),
                    "market": details.get("market", "stocks"),
                    "locale": details.get("locale", "us"),
                    "primary_exchange": details.get("primary_exchange", "NASDAQ"),
                    "type": details.get("type", "CS"),
                    "active": details.get("active", True),
                    "currency_name": details.get("currency_name", "USD"),
                    "cik": details.get("cik"),
                    "composite_figi": details.get("composite_figi"),
                    "share_class_figi": details.get("share_class_figi"),
                    "last_updated_utc": details.get("last_updated_utc"),
                    "delisted_utc": details.get("delisted_utc"),
                    "fetched_at": datetime.utcnow().isoformat()
                }
                return complete_data
            else:
                return self._get_fallback_stock_data(symbol)

        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {e}")
            return self._get_fallback_stock_data(symbol)

    def _get_fallback_stock_data(self, symbol: str) -> dict:
        """Get fallback data when API calls fail."""
        return {
            "symbol": symbol,
            "name": symbol,
            "price": None,
            "change": None,
            "change_percent": None,
            "high": None,
            "low": None,
            "open": None,
            "volume": None,
            "avg_volume": None,
            "market_cap": None,
            "pe_ratio": None,
            "description": None,
            "ceo": None,
            "employees": None,
            "headquarters": None,
            "founded": None,
            "sparkline_data": None,
            "logo_url": None,
            # Default values
            "market": "stocks",
            "locale": "us",
            "primary_exchange": "NASDAQ",
            "type": "CS",
            "active": True,
            "currency_name": "USD",
            "cik": None,
            "composite_figi": None,
            "share_class_figi": None,
            "last_updated_utc": None,
            "delisted_utc": None,
            "fetched_at": datetime.utcnow().isoformat()
        }

    async def _refresh_cache(self):
        """Refresh the entire cache with fresh data."""
        if self.is_refreshing:
            return  # Already refreshing

        self.is_refreshing = True
        try:
            logger.info("Refreshing popular stocks cache...")

            tasks = [self._fetch_popular_stock_data(symbol) for symbol in self.popular_stocks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            new_cache = {}
            for symbol, result in zip(self.popular_stocks, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to fetch {symbol}: {result}")
                    new_cache[symbol] = self._get_fallback_stock_data(symbol)
                else:
                    new_cache[symbol] = result

            self.cache = new_cache
            self.cache_timestamp = time.time()

            logger.info(f"Cache refreshed with {len(new_cache)} stocks")

        except Exception as e:
            logger.error(f"Error refreshing cache: {e}")
        finally:
            self.is_refreshing = False

    async def get_popular_stocks(self, limit: Optional[int] = None) -> List[dict]:
        """Get popular stocks, refreshing cache if needed."""
        if not self._is_cache_valid() or self._should_refresh():
            await self._refresh_cache()

        stocks = list(self.cache.values())
        if limit:
            stocks = stocks[:limit]

        return stocks

    async def get_popular_stock(self, symbol: str) -> Optional[dict]:
        """Get a specific popular stock."""
        if symbol not in self.popular_stocks:
            return None

        if not self._is_cache_valid():
            await self._refresh_cache()

        return self.cache.get(symbol)

    def clear_cache(self):
        """Clear the cache manually."""
        self.cache = {}
        self.cache_timestamp = None
        logger.info("Popular stocks cache cleared")

popular_stocks_cache = PopularStocksCache()
