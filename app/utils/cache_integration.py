from typing import Dict, Any, List, Optional
from app.utils.service_registry import services

class CacheIntegration:
    
    @staticmethod
    def invalidate_user_data(user_id: int, email: Optional[str] = None):
        from app.utils.cache import delete
        
        patterns = [
            f"user:profile:{user_id}",
            f"user:contexts:{user_id}",
            f"balance:user:{user_id}",
            f"portfolio:user:{user_id}:0:100",
            f"watchlists:user:{user_id}:0:100",
            f"trades:user:{user_id}:0:100",
            f"notifications:user:{user_id}:0:50",
            f"notifications:unread:{user_id}",
            f"notifications:recent:{user_id}",
            f"progress:user:{user_id}:recent",
            f"permissions:user:{user_id}:school:*",
            f"user:roles:{user_id}:school:*"
        ]
        
        if email:
            patterns.append(f"user:by_email:{email.lower()}")
        
        for pattern in patterns:
            delete(pattern)
    
    @staticmethod
    def invalidate_school_data(school_id: int):
        from app.utils.cache import delete
        
        patterns = [
            f"school:details:{school_id}",
            f"school:students:{school_id}:0:100",
            f"school:teachers:{school_id}:0:100",
            f"courses:school:{school_id}:0:100",
            f"report:user_activity:{school_id}:30",
            f"report:trading_leaderboard:{school_id}",
            f"report:school_performance:{school_id}"
        ]
        
        for pattern in patterns:
            delete(pattern)
    
    @staticmethod
    def invalidate_course_data(course_id: int, school_id: Optional[int] = None):
        from app.utils.cache import delete
        
        patterns = [
            f"exam:details:{course_id}",
            f"exam:questions:{course_id}",
            f"progress:course:{course_id}:overview",
            f"report:course_analytics:{course_id}"
        ]
        
        if school_id:
            patterns.extend([
                f"courses:school:{school_id}:0:100",
                f"school:details:{school_id}"
            ])
        
        for pattern in patterns:
            delete(pattern)
    
    @staticmethod
    def invalidate_trading_data(user_id: int):
        from app.utils.cache import delete
        
        patterns = [
            f"balance:user:{user_id}",
            f"portfolio:user:{user_id}:0:100",
            f"watchlists:user:{user_id}:0:100",
            f"trades:user:{user_id}:0:100",
            f"trading_summary_{user_id}",
            f"report:trading_leaderboard:None"
        ]
        
        for pattern in patterns:
            delete(pattern)
    
    @staticmethod
    def invalidate_admin_data():
        from app.utils.cache import delete
        
        patterns = [
            "report:dashboard:admin",
            "permissions:all",
            "school:list:0:100",
            "popular_stocks:all:None"
        ]
        
        for pattern in patterns:
            delete(pattern)

cache_integration = CacheIntegration()