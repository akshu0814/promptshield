import time
import logging
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# In-memory store: {ip: [timestamp, timestamp, ...]}
_request_counts: dict[str, list[float]] = defaultdict(list)

# Config
RATE_LIMIT_REQUESTS = 60    # max requests
RATE_LIMIT_WINDOW = 60      # per N seconds
RATE_LIMIT_ENABLED = True


def _get_client_ip(request: Request) -> str:
    """Get real client IP, checking proxy headers first."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _clean_old_requests(ip: str, now: float) -> None:
    """Remove timestamps older than the window."""
    cutoff = now - RATE_LIMIT_WINDOW
    _request_counts[ip] = [t for t in _request_counts[ip] if t > cutoff]


async def rate_limit_middleware(request: Request, call_next):
    """
    Sliding window rate limiter.
    Allows RATE_LIMIT_REQUESTS per RATE_LIMIT_WINDOW seconds per IP.
    Only applies to POST /scan — read endpoints are not limited.
    """
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    # Only rate limit the scan endpoint
    if request.url.path != "/scan" or request.method != "POST":
        return await call_next(request)

    ip = _get_client_ip(request)
    now = time.time()

    _clean_old_requests(ip, now)
    request_count = len(_request_counts[ip])

    if request_count >= RATE_LIMIT_REQUESTS:
        logger.warning(
            "Rate limit exceeded for IP %s — %d requests in %ds window",
            ip, request_count, RATE_LIMIT_WINDOW
        )
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds.",
                "retry_after": RATE_LIMIT_WINDOW,
            },
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    _request_counts[ip].append(now)

    # Add rate limit headers to response
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT_REQUESTS - request_count - 1)
    response.headers["X-RateLimit-Reset"] = str(int(now + RATE_LIMIT_WINDOW))
    return response
