"""
Tenant Context Middleware — extracts tenant_id from JWT and injects into request state.

Architecture:
  Request → TenantContextMiddleware → extract JWT from Authorization header
    → decode claims → get tenant_id → store in request.state.tenant_context
    → pass to route handler

Every route handler can then access:
  request.state.tenant_context  — dict with tenant_id, plan, tenant info

The tenant_id is also passed to:
  - CrewAI agent contexts (beehive) via tenant_context.set_current_tenant()
  - RLS data stores for automatic filtering
"""

import json
import logging
import time
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from models.tenant import get_tenant, get_plan_limits

logger = logging.getLogger("AgeixAI.middleware.tenant")

# ═══════════════════════════════════════════════════════════════════════════════
# JWT Configuration
# ═══════════════════════════════════════════════════════════════════════════════

# In production, this is your RS256 public key from the identity provider.
# For the mock, we use a simple HMAC secret and accept a static test token.
JWT_SECRET = "ageixai-mock-jwt-secret-do-not-use-in-production"
JWT_ALGORITHM = "HS256"

# Static API keys for quick testing (bypass JWT validation)
STATIC_API_KEYS: dict[str, str] = {
    "sk-demo-test":     "demo",
    "sk-acme-prod":     "acme",
    "sk-megacorp-prod": "megacorp",
}

# Tenant ID that will be used if no auth header is present (for open endpoints)
PUBLIC_TENANT_ID = "demo"


class TenantContext:
    """
    Thread-safe tenant context carrier.
    Stored on request.state so it's available to all downstream handlers.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.tenant_info: dict[str, Any] = get_tenant(tenant_id) or {}
        self.plan_limits: dict[str, Any] = get_plan_limits(tenant_id)
        self.plan_name: str = self.plan_limits.get("plan_name", "starter")

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "plan": self.plan_name,
            "tenant_name": self.tenant_info.get("name", ""),
            "features": self.plan_limits.get("features", []),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# JWT helpers (mock)
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_tenant_id_from_jwt(token: str) -> str | None:
    """
    Decode a JWT and extract tenant_id from claims.

    In production:
      payload = jwt.decode(token, JWT_PUBLIC_KEY, algorithms=["RS256"])
      return payload.get("tenant_id")

    Mock implementation: accepts a development JWT format or a static API key.
    """
    # Check static API keys first (for quick testing / machine-to-machine)
    if token in STATIC_API_KEYS:
        return STATIC_API_KEYS[token]

    # Mock JWT: base64-decode the payload and look for tenant_id
    try:
        parts = token.split(".")
        if len(parts) == 3:
            import base64
            padded = parts[1] + "=="
            decoded = base64.urlsafe_b64decode(padded)
            claims = json.loads(decoded)
            tid = claims.get("tenant_id") or claims.get("sub", "").split("@")[-1]
            if tid and get_tenant(tid):
                return tid
    except Exception:
        pass

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Middleware
# ═══════════════════════════════════════════════════════════════════════════════

SKIP_PATHS = {"/docs", "/redoc", "/openapi.json", "/api/health", "/api/tenant/register"}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that:
      1. Extracts tenant_id from the Authorization header (JWT or static key).
      2. Validates the tenant exists and is active.
      3. Stores TenantContext on request.state for downstream use.
      4. Calls rate_limiter.check_api_rate_limit() before passing to handler.
      5. Tracks the API call for metering.

    Routes annotated with @no_tenant_auth skip tenant validation.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path

        # Skip auth for open endpoints
        if any(path.startswith(sp) for sp in SKIP_PATHS):
            request.state.tenant_context = TenantContext(PUBLIC_TENANT_ID)
            return await call_next(request)

        # Extract tenant_id from Authorization header
        auth_header = request.headers.get("Authorization", "")
        tenant_id: str | None = None

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            tenant_id = _extract_tenant_id_from_jwt(token)
        elif auth_header.startswith("ApiKey "):
            api_key = auth_header[7:]
            tenant_id = STATIC_API_KEYS.get(api_key)
        elif auth_header and " " not in auth_header:
            # Allow raw API key in Authorization header
            tenant_id = STATIC_API_KEYS.get(auth_header)

        # Fallback: check X-Tenant-ID header for dev/testing
        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID")

        # Final fallback for internal routes
        if not tenant_id:
            tenant_id = PUBLIC_TENANT_ID

        # Validate tenant
        tenant = get_tenant(tenant_id)
        if not tenant:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": f"Invalid tenant: '{tenant_id}'"},
            )
        if not tenant.get("is_active", False):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": f"Tenant '{tenant_id}' is deactivated"},
            )

        # Build context and attach to request
        request.state.tenant_context = TenantContext(tenant_id)

        # Track the API call
        try:
            from models.tenant import track_api_call, check_api_rate_limit

            rate_check = check_api_rate_limit(tenant_id)
            if not rate_check["allowed"]:
                from fastapi.responses import JSONResponse
                logger.warning(
                    "Rate limit hit for tenant %s: %s",
                    tenant_id, rate_check["detail"],
                )
                return JSONResponse(
                    status_code=rate_check.get("status_code", 429),
                    content={"detail": rate_check["detail"]},
                )
            track_api_call(tenant_id)
        except Exception:
            logger.exception("Rate limiter error — allowing request")

        # Log the request
        logger.debug(
            "Tenant=%s plan=%s %s %s",
            tenant_id,
            request.state.tenant_context.plan_name,
            request.method,
            path,
        )

        # Forward the request and add tenant headers to response
        response: Response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        response.headers["X-Plan"] = request.state.tenant_context.plan_name

        return response
