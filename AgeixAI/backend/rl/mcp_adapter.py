"""
MCP Adapter for the RL Adaptive Learner.

The AI Orchestrator NEVER calls the adaptive learner directly.
All communication goes through this MCP adapter, maintaining the
plug-and-play modular architecture pattern where every module
is accessed via a secure API call.
"""

from typing import Any
from .adaptive_learner import (
    apply_feedback,
    get_rl_stats,
    get_ttp_weight,
    get_all_ttp_weights,
    get_feedback_log,
    _FEEDBACK_LOG,
)

SERVER_NAME = "rl"

SUPPORTED_ACTIONS = {
    "apply_feedback": "Record human feedback and update TTP weights",
    "get_stats": "Get RL accuracy score and learning progress",
    "get_ttp_weight": "Get the learned weight for a specific TTP technique",
    "get_all_ttp_weights": "Get all current TTP confidence weights",
    "get_feedback_log": "Get paginated feedback history",
}

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "apply_feedback":
        result = apply_feedback(
            decision_id=params.get("decision_id", "unknown"),
            threat_context=params.get("threat_context", ""),
            ai_recommendation=params.get("ai_recommendation", ""),
            ai_confidence=params.get("ai_confidence", 50.0),
            human_decision=params.get("human_decision", "rejected"),
            ttp_ids=params.get("ttp_ids"),
            risk_score=params.get("risk_score", 50.0),
        )
        return [{"status": "ok", "data": result}]

    elif action == "get_stats":
        stats = get_rl_stats()
        return [{"status": "ok", "data": stats}]

    elif action == "get_ttp_weight":
        ttp_id = params.get("ttp_id", "")
        weight = get_ttp_weight(ttp_id)
        return [{"status": "ok", "data": {"ttp_id": ttp_id, "weight": weight}}]

    elif action == "get_all_ttp_weights":
        weights = get_all_ttp_weights()
        return [{"status": "ok", "data": weights}]

    elif action == "get_feedback_log":
        limit = params.get("limit", 20)
        offset = params.get("offset", 0)
        entries = get_feedback_log(limit=limit, offset=offset)
        return [{"status": "ok", "data": {"entries": entries, "total": len(_FEEDBACK_LOG)}}]

    return [{"status": "error", "error": f"Unknown action: {action}"}]
