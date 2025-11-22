from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import logging

from app.core.decorators import cache_trading_data, cache_stock_data, CacheKeys, invalidate_cache
from app.services.trading import trading_service
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

class CachedTradingService:

    @cache_trading_data(ttl=30)
    async def get_user_portfolio(self, db: Session, user_id: int) -> Dict[str, Any]:
        return trading_service.get_user_portfolio(db, user_id=user_id)

    @cache_trading_data(ttl=60)
    async def get_user_balance(self, db: Session, user_id: int) -> Dict[str, Any]:
        return trading_service.get_user_balance(db, user_id=user_id)

    @cache_trading_data(ttl=120)
    async def get_trade_history(self, db: Session, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        return trading_service.get_trade_history(db, user_id=user_id, limit=limit)

    @cache_stock_data(ttl=30)
    async def get_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        return await trading_service.get_current_price(symbol)

    @cache_stock_data(ttl=60)
    async def get_popular_stocks(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        from app.services.popular_stocks_cache import popular_stocks_cache
        return await popular_stocks_cache.get_popular_stocks(limit=limit)

    async def execute_trade(self, db: Session, user_id: int, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = trading_service.execute_trade(db, user_id=user_id, **trade_data)

            await cache_service.invalidate_trading_cache(user_id)

            symbol = trade_data.get('symbol')
            if symbol:
                await cache_service.invalidate_stock_cache(symbol)

            return result
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            raise

    async def update_watchlist(self, db: Session, user_id: int, action: str, symbol: str) -> Dict[str, Any]:
        try:
            result = trading_service.update_watchlist(db, user_id=user_id, action=action, symbol=symbol)

            await cache_service.invalidate_trading_cache(user_id)

            return result
        except Exception as e:
            logger.error(f"Watchlist update failed: {e}")
            raise

cached_trading_service = CachedTradingService()