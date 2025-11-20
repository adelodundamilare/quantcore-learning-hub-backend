"""Cache configuration and TTL settings"""

# Cache TTL (Time To Live) configurations in seconds
CACHE_TTL = {
    # User data - changes infrequently
    "user_profile": 600,      # 10 minutes
    "user_contexts": 300,     # 5 minutes
    "user_by_email": 900,     # 15 minutes
    
    # Course data - moderately stable
    "course_details": 600,    # 10 minutes
    "courses_by_school": 300, # 5 minutes
    "user_courses": 180,      # 3 minutes
    "course_list": 300,       # 5 minutes
    
    # School data - very stable
    "school_details": 900,    # 15 minutes
    "school_students": 300,   # 5 minutes
    "school_teachers": 300,   # 5 minutes
    "school_list": 600,       # 10 minutes
    
    # Trading data - needs frequent updates
    "account_balance": 60,    # 1 minute
    "portfolio": 120,         # 2 minutes
    "watchlists": 180,        # 3 minutes
    "trade_history": 300,     # 5 minutes
    "trading_summary": 300,   # 5 minutes
    
    # Stock data - very dynamic
    "stock_price": 30,        # 30 seconds
    "popular_stocks": 300,    # 5 minutes
    "stock_details": 600,     # 10 minutes
}

# Cache key patterns
CACHE_KEYS = {
    "user_profile": "user:profile:{}",
    "user_contexts": "user:contexts:{}",
    "user_by_email": "user:by_email:{}",
    
    "course_details": "course:details:{}",
    "courses_by_school": "courses:school:{}:{}:{}",
    "user_courses": "courses:user:{}:{}",
    
    "school_details": "school:details:{}",
    "school_students": "school:students:{}:{}:{}",
    "school_teachers": "school:teachers:{}:{}:{}",
    
    "account_balance": "balance:user:{}",
    "portfolio": "portfolio:user:{}:{}:{}",
    "watchlists": "watchlists:user:{}:{}:{}",
    "trade_history": "trades:user:{}:{}:{}",
    "trading_summary": "trading_summary_{}",
    
    "stock_price": "stock:price:{}",
    "popular_stocks": "stock:popular",
    "stock_details": "stock:details:{}",
}

# Cache invalidation patterns - what to clear when data changes
INVALIDATION_PATTERNS = {
    "user_update": [
        "user:profile:{}",
        "user:contexts:{}",
        "courses:user:{}:*"
    ],
    "course_update": [
        "course:details:{}",
        "courses:school:*",
        "courses:user:*"
    ],
    "school_update": [
        "school:details:{}",
        "school:students:{}:*",
        "school:teachers:{}:*",
        "courses:school:{}:*"
    ],
    "trade_execution": [
        "balance:user:{}",
        "portfolio:user:{}:*",
        "trades:user:{}:*",
        "trading_summary_{}"
    ]
}