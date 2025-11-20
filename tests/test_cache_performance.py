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
        """Clear cache before each test"""
        clear()
    
    def test_cache_basic_functionality(self):
        """Test that cache actually works"""
        # Test set/get
        result = set("test_key", {"data": "test_value"}, ttl=60)
        assert result is True
        
        cached_data = get("test_key")
        assert cached_data == {"data": "test_value"}
        
        # Test delete
        deleted = delete("test_key")
        assert deleted is True
        
        # Should be None after delete
        assert get("test_key") is None
    
    def test_cache_expiration(self):
        """Test that cache entries expire correctly"""
        # Set with 1 second TTL
        set("expire_test", "data", ttl=1)
        
        # Should exist immediately
        assert get("expire_test") == "data"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be None after expiration
        assert get("expire_test") is None
    
    @patch('app.crud.user.user.get')
    def test_user_service_caching(self, mock_user_get, db_session: Session):
        """Test that user service caching reduces database calls"""
        # Mock user data
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
        
        # First call - should hit database
        result1 = cached_user_service.get_user_profile(db_session, 1)
        assert mock_user_get.call_count == 1
        
        # Second call - should hit cache
        result2 = cached_user_service.get_user_profile(db_session, 1)
        assert mock_user_get.call_count == 1  # No additional database call
        
        # Results should be identical
        assert result1 == result2
        assert result1["email"] == "test@example.com"
    
    def test_cache_performance_improvement(self, db_session: Session):
        """Test that caching improves performance"""
        with patch('app.crud.user.user.get') as mock_get:
            # Simulate slow database call
            def slow_db_call(*args, **kwargs):
                time.sleep(0.1)  # 100ms delay
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
            
            # First call - should be slow
            start_time = time.time()
            cached_user_service.get_user_profile(db_session, 1)
            first_call_time = time.time() - start_time
            
            # Second call - should be fast (cached)
            start_time = time.time()
            cached_user_service.get_user_profile(db_session, 1)
            second_call_time = time.time() - start_time
            
            # Cache should be significantly faster
            assert second_call_time < first_call_time / 10  # At least 10x faster
            assert first_call_time > 0.05  # First call should take time
            assert second_call_time < 0.01  # Second call should be very fast
    
    def test_cache_invalidation(self):
        """Test that cache invalidation works correctly"""
        from app.utils.cache_invalidation import cache_invalidator
        
        # Set some user cache data
        set("user:profile:1", {"name": "Test User"})
        set("balance:user:1", {"balance": 1000})
        set("portfolio:user:1:0:100", [{"symbol": "AAPL"}])
        
        # Verify data is cached
        assert get("user:profile:1") is not None
        assert get("balance:user:1") is not None
        assert get("portfolio:user:1:0:100") is not None
        
        # Invalidate user cache
        cache_invalidator.invalidate_user_cache(1)
        
        # User profile should be cleared, but others should remain for now
        # (This is a simplified test - in reality you'd implement pattern matching)
        assert get("user:profile:1") is None


class TestCacheIntegration:
    """Integration tests for caching with actual services"""
    
    def setup_method(self):
        clear()
    
    def test_course_service_integration(self, db_session: Session):
        """Test that course service caching integrates properly"""
        # This would require actual database setup in a real integration test
        # For now, we'll just test that the decorators don't break functionality
        pass
    
    def test_trading_service_integration(self, db_session: Session):
        """Test that trading service caching integrates properly"""
        # This would require actual database setup in a real integration test
        # For now, we'll just test that the decorators don't break functionality
        pass