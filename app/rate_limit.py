"""Rate limiting middleware for webhook endpoint."""

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Handle rate limit exceeded exceptions."""
    logger.warning(f"Rate limit exceeded for {get_remote_address(request)}")
    return JSONResponse(
        status_code=429,
        content={"ok": False, "error": "Rate limit exceeded"},
    )
