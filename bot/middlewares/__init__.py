"""
Middleware для бота
"""

from .rate_limit_middleware import RateLimitMiddleware

__all__ = ["RateLimitMiddleware"]
