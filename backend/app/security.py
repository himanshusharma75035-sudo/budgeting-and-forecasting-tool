"""HTTP hardening middleware (defence-in-depth for a local-first service).

Everything here is intentionally **dependency-free** (pure Starlette/ASGI) so it adds zero
supply-chain surface. It implements:

* ``SecurityHeadersMiddleware`` — the OWASP "secure headers" baseline (CSP, anti-clickjacking,
  nosniff, referrer/permissions policy, cross-origin isolation, optional HSTS).
* ``MaxBodySizeMiddleware``     — rejects oversized request bodies (DoS / memory-exhaustion guard).
* ``RateLimitMiddleware``       — a sliding-window, per-client in-process rate limiter.

All thresholds are read from :data:`app.config.settings` at request time, so they can be tuned
via ``OPENFPA_*`` environment variables and overridden in tests. See ``SECURITY.md``.
"""

from __future__ import annotations

import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach OWASP-recommended hardening headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        h.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        h.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        h.setdefault("Permissions-Policy", settings.permissions_policy)
        h.setdefault("Content-Security-Policy", settings.content_security_policy)
        if settings.enable_hsts:
            h.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        # Don't advertise the framework/version.
        h["Server"] = "openfpa"
        return response


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared body exceeds ``settings.max_request_bytes``."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length header."}, status_code=400)
            if declared > settings.max_request_bytes:
                return JSONResponse(
                    {"detail": "Request body too large.", "limit_bytes": settings.max_request_bytes},
                    status_code=413,
                )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window, per-client-IP rate limiter (in-process, single-worker scope).

    Suitable for a local-first / single-user deployment. For a multi-worker or multi-host
    deployment, front the service with a shared limiter (e.g. a reverse proxy or Redis).
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._hits: dict[str, deque[float]] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        client = request.client.host if request.client else "anonymous"
        now = time.monotonic()
        window = 60.0
        bucket = self._hits.setdefault(client, deque())
        while bucket and now - bucket[0] > window:
            bucket.popleft()

        if len(bucket) >= settings.rate_limit_per_minute:
            retry_after = int(window - (now - bucket[0])) + 1
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please retry later."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        return await call_next(request)
