"""
AgeixAISOC Multi-Tenancy — Tenant model, subscription plans, and RLS simulation.

In production, this maps to:
  - A `tenants` PostgreSQL table with RLS policies
  - A `tenant_usage` table for metering
  - A `tenant_endpoints` table for endpoint registration

RLS policies (PostgreSQL — applied via migration):
  CREATE POLICY tenant_isolation ON alerts USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
  CREATE POLICY tenant_isolation ON decisions USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
  CREATE POLICY tenant_isolation ON audit_trail USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
  ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
  ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
  ALTER TABLE audit_trail ENABLE ROW LEVEL SECURITY;
"""

import hashlib
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger("AgeixAI.tenant")

# ── Subscription Plans ───────────────────────────────────────────────────────

SUBSCRIPTION_PLANS: dict[str, dict[str, Any]] = {
    "starter": {
        "name": "Starter",
        "max_endpoints": 50,
        "max_api_calls_per_min": 60,
        "max_ai_tokens_per_month": 500_000,
        "max_users": 5,
        "features": ["basic_alerts", "manual_threat_hunt", "email_reports"],
        "price_monthly": 0,
    },
    "pro": {
        "name": "Professional",
        "max_endpoints": 500,
        "max_api_calls_per_min": 600,
        "max_ai_tokens_per_month": 5_000_000,
        "max_users": 25,
        "features": ["basic_alerts", "auto_threat_hunt", "ueba", "deception", "slack_pagerduty", "api_access"],
        "price_monthly": 299,
    },
    "enterprise": {
        "name": "Enterprise",
        "max_endpoints": 10000,
        "max_api_calls_per_min": 6000,
        "max_ai_tokens_per_month": 50_000_000,
        "max_users": 999,
        "features": ["all_pro_features", "custom_integrations", "dedicated_support", "on_prem_deployment", "sla"],
        "price_monthly": 999,
    },
}

# ── Tenant database (in-memory; in production this is PostgreSQL) ────────────

_TENANTS: dict[str, dict[str, Any]] = {
    "demo": {
        "tenant_id": "demo",
        "name": "Demo Corporation",
        "plan": "starter",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
        "contact_email": "demo@example.com",
    },
    "acme": {
        "tenant_id": "acme",
        "name": "Acme Security Inc.",
        "plan": "pro",
        "is_active": True,
        "created_at": "2026-03-15T00:00:00Z",
        "contact_email": "admin@acmesec.com",
    },
    "megacorp": {
        "tenant_id": "megacorp",
        "name": "MegaCorp International",
        "plan": "enterprise",
        "is_active": True,
        "created_at": "2025-11-01T00:00:00Z",
        "contact_email": "soc@megacorp.com",
    },
}

# ── Usage tracking ──────────────────────────────────────────────────────────

_USAGE: dict[str, dict[str, Any]] = {}


def _ensure_tenant_usage(tenant_id: str) -> dict[str, Any]:
    if tenant_id not in _USAGE:
        _USAGE[tenant_id] = {
            "tenant_id": tenant_id,
            "api_calls_total": 0,
            "api_calls_minute": 0,
            "api_calls_minute_reset": time.time(),
            "ai_tokens_used": 0,
            "ai_tokens_month": 0,
            "endpoints_connected": 0,
            "alerts_ingested": 0,
            "decisions_made": 0,
            "last_api_call": None,
        }
    return _USAGE[tenant_id]


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def get_tenant(tenant_id: str) -> dict[str, Any] | None:
    """Return tenant info or None if not found."""
    return _TENANTS.get(tenant_id)


def get_tenant_or_raise(tenant_id: str) -> dict[str, Any]:
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant '{tenant_id}' not found")
    if not tenant.get("is_active", False):
        raise ValueError(f"Tenant '{tenant_id}' is deactivated")
    return tenant


def get_plan_limits(tenant_id: str) -> dict[str, Any]:
    """Return the subscription plan limits for a tenant."""
    tenant = get_tenant_or_raise(tenant_id)
    plan_name = tenant.get("plan", "starter")
    plan = SUBSCRIPTION_PLANS.get(plan_name, SUBSCRIPTION_PLANS["starter"])
    return {**plan, "plan_name": plan_name}


# ═══════════════════════════════════════════════════════════════════════════════
# Rate Limiting & Quota Checks
# ═══════════════════════════════════════════════════════════════════════════════

def check_api_rate_limit(tenant_id: str) -> dict[str, Any]:
    """
    Check if the tenant has exceeded rate limits.
    Returns {"allowed": True} or {"allowed": False, "status_code": 429, "detail": "..."}.
    """
    usage = _ensure_tenant_usage(tenant_id)
    plan = get_plan_limits(tenant_id)
    now = time.time()

    # Reset per-minute counter if a minute has passed
    if now - usage["api_calls_minute_reset"] >= 60:
        usage["api_calls_minute"] = 0
        usage["api_calls_minute_reset"] = now

    max_per_min = plan["max_api_calls_per_min"]
    if usage["api_calls_minute"] >= max_per_min:
        return {
            "allowed": False,
            "status_code": 429,
            "detail": f"Rate limit exceeded: {usage['api_calls_minute']}/{max_per_min} calls/minute. "
                      f"Upgrade from {plan['plan_name'].title()} to increase limit.",
        }

    # Check endpoint limit (rate-based check)
    max_endpoints = plan["max_endpoints"]
    if usage["endpoints_connected"] > max_endpoints:
        return {
            "allowed": False,
            "status_code": 402,
            "detail": f"Endpoint limit exceeded: {usage['endpoints_connected']}/{max_endpoints} endpoints. "
                      f"Upgrade from {plan['plan_name'].title()} to connect more endpoints.",
        }

    return {"allowed": True}


def track_api_call(tenant_id: str) -> None:
    """Increment API call counter for rate limiting."""
    usage = _ensure_tenant_usage(tenant_id)
    usage["api_calls_total"] += 1
    usage["api_calls_minute"] += 1
    usage["last_api_call"] = datetime.now(timezone.utc).isoformat()


def track_ai_tokens(tenant_id: str, tokens: int) -> dict[str, Any]:
    """
    Track AI token consumption. Returns warning if approaching limit.
    """
    usage = _ensure_tenant_usage(tenant_id)
    plan = get_plan_limits(tenant_id)
    usage["ai_tokens_used"] += tokens
    usage["ai_tokens_month"] += tokens

    max_tokens = plan["max_ai_tokens_per_month"]
    pct = (usage["ai_tokens_month"] / max_tokens) * 100 if max_tokens > 0 else 0

    if usage["ai_tokens_month"] >= max_tokens:
        return {
            "blocked": True,
            "detail": f"AI token quota exhausted: {usage['ai_tokens_month']:,}/{max_tokens:,} tokens this month. "
                      f"Upgrade plan to continue using AI features.",
        }
    if pct >= 80:
        return {
            "warning": True,
            "detail": f"AI token usage at {pct:.0f}% ({usage['ai_tokens_month']:,}/{max_tokens:,}). "
                      f"Consider upgrading plan.",
            "pct": round(pct, 1),
        }
    return {"ok": True, "pct": round(pct, 1)}


def track_endpoint_registration(tenant_id: str, count: int = 1) -> dict[str, Any]:
    """Increment endpoint count; blocks ingestion if over plan limit."""
    usage = _ensure_tenant_usage(tenant_id)
    plan = get_plan_limits(tenant_id)
    usage["endpoints_connected"] += count

    max_eps = plan["max_endpoints"]
    if usage["endpoints_connected"] > max_eps:
        return {
            "allowed": False,
            "status_code": 402,
            "detail": f"Endpoint limit exceeded: {usage['endpoints_connected']}/{max_eps}. "
                      f"Payment Required — upgrade from {plan['plan_name'].title()} to connect more endpoints.",
        }
    return {"allowed": True, "current": usage["endpoints_connected"], "limit": max_eps}


def track_alert_ingested(tenant_id: str) -> None:
    usage = _ensure_tenant_usage(tenant_id)
    usage["alerts_ingested"] += 1


def track_decision_made(tenant_id: str) -> None:
    usage = _ensure_tenant_usage(tenant_id)
    usage["decisions_made"] += 1


# ═══════════════════════════════════════════════════════════════════════════════
# RLS Simulation — Tenant-scoped data stores
# ═══════════════════════════════════════════════════════════════════════════════
#
# In production, PostgreSQL RLS policies enforce this automatically.
# For the in-memory mock, we partition data by tenant_id.

_ALERTS_BY_TENANT: dict[str, list[dict[str, Any]]] = {}
_DECISIONS_BY_TENANT: dict[str, list[dict[str, Any]]] = {}
_AUDIT_BY_TENANT: dict[str, list[dict[str, Any]]] = {}


def rls_insert(store_name: str, tenant_id: str, record: dict[str, Any]) -> dict[str, Any]:
    """Insert a record into a tenant-scoped store."""
    record["tenant_id"] = tenant_id
    stores = {
        "alerts": _ALERTS_BY_TENANT,
        "decisions": _DECISIONS_BY_TENANT,
        "audit": _AUDIT_BY_TENANT,
    }
    store = stores.get(store_name)
    if store is None:
        raise ValueError(f"Unknown RLS store: {store_name}")
    if tenant_id not in store:
        store[tenant_id] = []
    store[tenant_id].append(record)
    return record


def rls_query(store_name: str, tenant_id: str, **filters: Any) -> list[dict[str, Any]]:
    """
    Query a tenant-scoped store — automatically filters by tenant_id.
    This simulates PostgreSQL RLS: `WHERE tenant_id = current_setting(...)`.
    """
    stores = {
        "alerts": _ALERTS_BY_TENANT,
        "decisions": _DECISIONS_BY_TENANT,
        "audit": _AUDIT_BY_TENANT,
    }
    store = stores.get(store_name)
    if store is None:
        raise ValueError(f"Unknown RLS store: {store_name}")

    records = store.get(tenant_id, [])
    if filters:
        result = []
        for r in records:
            match = True
            for key, value in filters.items():
                if r.get(key) != value:
                    match = False
                    break
            if match:
                result.append(r)
        return result
    return list(records)


def rls_delete(store_name: str, tenant_id: str, record_id: str, id_field: str = "id") -> bool:
    """Delete a single record from a tenant-scoped store."""
    stores = {
        "alerts": _ALERTS_BY_TENANT,
        "decisions": _DECISIONS_BY_TENANT,
        "audit": _AUDIT_BY_TENANT,
    }
    store = stores.get(store_name)
    if store is None or tenant_id not in store:
        return False
    original = store[tenant_id]
    store[tenant_id] = [r for r in original if r.get(id_field) != record_id]
    return len(store[tenant_id]) < len(original)


def rls_count(store_name: str, tenant_id: str) -> int:
    stores = {
        "alerts": _ALERTS_BY_TENANT,
        "decisions": _DECISIONS_BY_TENANT,
        "audit": _AUDIT_BY_TENANT,
    }
    store = stores.get(store_name)
    if store is None:
        return 0
    return len(store.get(tenant_id, []))


# ═══════════════════════════════════════════════════════════════════════════════
# Usage Metrics (for /api/tenant/usage endpoint)
# ═══════════════════════════════════════════════════════════════════════════════

def get_tenant_usage(tenant_id: str) -> dict[str, Any]:
    """Return full usage metrics for a tenant."""
    usage = _ensure_tenant_usage(tenant_id)
    plan = get_plan_limits(tenant_id)

    return {
        "tenant_id": tenant_id,
        "plan": plan["plan_name"],
        "limits": {
            "max_endpoints": plan["max_endpoints"],
            "max_api_calls_per_min": plan["max_api_calls_per_min"],
            "max_ai_tokens_per_month": plan["max_ai_tokens_per_month"],
            "max_users": plan["max_users"],
        },
        "current_usage": {
            "api_calls_total": usage["api_calls_total"],
            "api_calls_this_minute": usage["api_calls_minute"],
            "ai_tokens_used": usage["ai_tokens_used"],
            "ai_tokens_month": usage["ai_tokens_month"],
            "endpoints_connected": usage["endpoints_connected"],
            "alerts_ingested": usage["alerts_ingested"],
            "decisions_made": usage["decisions_made"],
        },
        "usage_percentages": {
            "api_calls_minute_pct": round(
                (usage["api_calls_minute"] / max(plan["max_api_calls_per_min"], 1)) * 100, 1
            ),
            "ai_tokens_month_pct": round(
                (usage["ai_tokens_month"] / max(plan["max_ai_tokens_per_month"], 1)) * 100, 1
            ),
            "endpoints_pct": round(
                (usage["endpoints_connected"] / max(plan["max_endpoints"], 1)) * 100, 1
            ),
        },
    }


def list_tenants() -> list[dict[str, Any]]:
    """List all tenants (admin only)."""
    return [
        {
            "tenant_id": tid,
            "name": t["name"],
            "plan": t["plan"],
            "is_active": t["is_active"],
        }
        for tid, t in _TENANTS.items()
    ]
