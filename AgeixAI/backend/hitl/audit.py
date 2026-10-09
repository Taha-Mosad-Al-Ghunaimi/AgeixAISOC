import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger("AgeixAI.hitl.audit")

_AUDIT_CHAIN: list[dict[str, Any]] = []

IMMUTABLE_ACTIONS = {"block_ip", "isolate_host", "deceive_attacker", "remediate", "kill_process", "update_rule", "xdr_isolate_host", "xdr_block_ip_fortigate"}


def _compute_hash(entry: dict[str, Any], previous_hash: str) -> str:
    data = json.dumps(entry, sort_keys=True, default=str) + previous_hash
    return hashlib.sha256(data.encode()).hexdigest()


def log_decision(
    action_id: str,
    action_type: str,
    target: str,
    source_agent: str,
    decision: Literal["pending", "approved", "rejected", "modified"],
    approved_by: str | None = None,
    modification: str | None = None,
) -> dict[str, Any]:
    previous_hash = _AUDIT_CHAIN[-1]["hash"] if _AUDIT_CHAIN else "GENESIS_BLOCK"

    entry = {
        "id": f"AUDIT-{len(_AUDIT_CHAIN) + 1:06d}",
        "action_id": action_id,
        "action_type": action_type,
        "target": target,
        "source_agent": source_agent,
        "decision": decision,
        "approved_by": approved_by,
        "modification": modification,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_at": datetime.now(timezone.utc).isoformat() if decision != "pending" else None,
        "previous_hash": previous_hash,
    }

    entry["hash"] = _compute_hash(entry, previous_hash)
    _AUDIT_CHAIN.append(entry)
    logger.info("Audit: action=%s decision=%s target=%s hash=%s", action_id, decision, target, entry["hash"][:16])
    return entry


def get_audit_trail(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    return _AUDIT_CHAIN[-limit - offset:len(_AUDIT_CHAIN) - offset] if _AUDIT_CHAIN else []


def verify_chain_integrity() -> bool:
    for i in range(1, len(_AUDIT_CHAIN)):
        expected_hash = _compute_hash(_AUDIT_CHAIN[i], _AUDIT_CHAIN[i - 1]["hash"])
        if _AUDIT_CHAIN[i]["hash"] != expected_hash:
            logger.error("Audit chain integrity VIOLATED at index %d", i)
            return False
    return True


def get_chain_length() -> int:
    return len(_AUDIT_CHAIN)
