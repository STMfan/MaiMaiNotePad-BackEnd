"""
Middleware configuration module
Provides unified middleware initialization and management
Includes: rate limiting, CORS, error handling, etc.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.logging import app_logger


def setup_middlewares(app: FastAPI) -> None:
    """
    Configure all middlewares for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        
    Middleware execution order (from outer to inner):
    1. ErrorHandlerMiddleware - Error handling and request logging (to be added)
    2. SlowAPIMiddleware - Rate limiting
    3. CORSMiddleware - CORS support
    """
    try:
        # 1. Initialize rate limiter
        app_logger.info("Initializing rate limiter...")
        limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app_logger.info("Rate limiter initialized")

        # 2. Add rate limiting middleware
        app_logger.info("Adding rate limiting middleware...")
        app.add_middleware(SlowAPIMiddleware)
        app_logger.info("Rate limiting middleware added")

        # 3. Add CORS middleware
        app_logger.info("Configuring CORS middleware...")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Should be configured with specific domains in production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["Content-Disposition"],
        )
        app_logger.info("CORS middleware configured")

        app_logger.info("All middlewares configured successfully")
        
    except Exception as e:
        app_logger.error(f"Middleware configuration failed: {str(e)}")
        raise
