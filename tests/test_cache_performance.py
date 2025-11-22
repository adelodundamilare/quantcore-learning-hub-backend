"""Performance tests for caching implementation"""
import time
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.utils.cache import get, set, delete, clear
from app.services.cached_user import cached_user_service
from app.services.cached_trading import cached_trading_service


class TestCachePerformance:

    def setup_method(self):
        clear()

    def test_cache_basic_functionality(self):
        result = set("test_key", {"data": "test_value"}, ttl=60)
        assert result is True

        cached_data = get("test_key")
        assert cached_data == {"data": "test_value"}

        deleted = delete("test_key")
        assert deleted is True

        assert get("test_key") is None

    def test_cache_expiration(self):
        set("expire_test", "data", ttl=1)

        assert get("expire_test") == "data"

        time.sleep(1.1)

        assert get("expire_test") is None

    @patch('app.crud.user.user.get')
    def test_user_service_caching(self, mock_user_get, db_session: Session):
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.full_name = "Test User"
        mock_user.is_active = True
        mock_user.created_at = None
        mock_user.updated_at = None

        mock_user_get.return_value = mock_user

        result1 = cached_user_service.get_user_profile(db_session, 1)
        assert mock_user_get.call_count == 1

        result2 = cached_user_service.get_user_profile(db_session, 1)
        assert mock_user_get.call_count == 1

        assert result1 == result2
        assert result1["email"] == "test@example.com"

    def test_cache_performance_improvement(self, db_session: Session):
        with patch('app.crud.user.user.get') as mock_get:
            def slow_db_call(*args, **kwargs):
                time.sleep(0.1)
                mock_user = Mock()
                mock_user.id = 1
                mock_user.email = "test@example.com"
                mock_user.first_name = "Test"
                mock_user.last_name = "User"
                mock_user.full_name = "Test User"
                mock_user.is_active = True
                mock_user.created_at = None
                mock_user.updated_at = None
                return mock_user

            mock_get.side_effect = slow_db_call

            start_time = time.time()
            cached_user_service.get_user_profile(db_session, 1)
            first_call_time = time.time() - start_time

            start_time = time.time()
            cached_user_service.get_user_profile(db_session, 1)
            second_call_time = time.time() - start_time

            assert second_call_time < first_call_time / 10
            assert first_call_time > 0.05
            assert second_call_time < 0.01

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        from app.services.cache_service import cache_service
        from app.core.cache import cache

        await cache.set("user:profile:1", {"name": "Test User"})
        await cache.set("balance:user:1", {"balance": 1000})
        await cache.set("portfolio:user:1:0:100", [{"symbol": "AAPL"}])

        assert await cache.get("user:profile:1") is not None
        assert await cache.get("balance:user:1") is not None
        assert await cache.get("portfolio:user:1:0:100") is not None

        await cache_service.invalidate_user_cache(1)

        assert await cache.get("user:profile:1") is None
        assert await cache.get("balance:user:1") is None
        assert await cache.get("portfolio:user:1:0:100") is None


class TestCacheIntegration:

    def setup_method(self):
        clear()

    def test_course_service_integration(self, db_session: Session):
        pass

    def test_trading_service_integration(self, db_session: Session):
        pass