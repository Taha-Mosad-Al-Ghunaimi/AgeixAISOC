"""
Adaptive RAG Learning — learns from every human decision.

Two entry points:
  learn_from_human(decision_package, human_action, analyst_notes)
    → Simple, opinionated API for explicit learning (WP4).

  learn_from_human_decision(...)
    → Legacy API used by the existing /api/human-decision and /api/decision/{id} paths.

Recall:
  inject_rag_context(alert_description, ...)
    → Queries ChromaDB "human_decisions_memory" collection for similar past incidents
       and returns structured context for Master Brain prompt injection.

Accuracy Tracking:
  Every decision stores whether the AI's recommendation matched the human's
  final decision. This feeds into `/api/brain-stats` as the "AI Accuracy Trend".
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from rag.vector_store import get_vector_store, VectorStore

logger = logging.getLogger("AgeixAI.adaptive_rag")

# ── In-memory accuracy trend ────────────────────────────────────────────────

_ACCURACY_LOG: list[dict[str, Any]] = []


# ══════════════════════════════════════════════════════════════════════════════
# 1. THE LEARNING FUNCTION
# ══════════════════════════════════════════════════════════════════════════════


def learn_from_human(
    decision_package: dict[str, Any],
    human_action: str,
    analyst_notes: str,
) -> dict[str, Any]:
    """
    Called when a human makes a decision on a Decision Package.

    Parameters
    ----------
    decision_package : dict
        Full alert context with keys: alert_id, title, description, severity,
        mitre_techniques, source_ip, ai_recommendation, ai_recommended_action,
        risk_score, risk_level, analyst_id.
    human_action : str
        One of "approved", "rejected", "modified".
    analyst_notes : str
        Free-text notes from the human analyst.

    Returns
    -------
    dict with doc_id, decision_id, and RAG memory size.
    """
    store = get_vector_store()

    alert_id = decision_package.get("alert_id", "unknown")
    title = decision_package.get("title", "Untitled Alert")
    description = decision_package.get("description", "")
    severity = decision_package.get("severity", "medium")
    mitre_techniques = decision_package.get("mitre_techniques", []) or []
    source_ip = decision_package.get("source_ip", "unknown")
    ai_recommendation = decision_package.get("ai_recommendation", "")
    ai_recommended_action = decision_package.get("ai_recommended_action", "")
    risk_score = decision_package.get("risk_score", 0.0)
    risk_level = decision_package.get("risk_level", "medium")
    analyst_id = decision_package.get("analyst_id", "human-analyst")

    technique_str = ", ".join(mitre_techniques) if mitre_techniques else "unknown"

    # Format into a rich descriptive document (semantic search will match on this)
    content = (
        f"ALERT: {title}\n"
        f"Description: {description}\n"
        f"Severity: {severity}  Risk Score: {risk_score}/100 ({risk_level})\n"
        f"Source IP: {source_ip}  MITRE Techniques: {technique_str}\n"
        f"AI Suggested: {ai_recommendation}\n"
        f"AI Recommended Action: {ai_recommended_action}\n"
        f"Human Decided: {human_action.upper()} because: {analyst_notes}\n"
        f"Analyst: {analyst_id}\n"
        f"Alert ID: {alert_id}\n"
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}"
    )

    doc_id = (
        f"LD-{hashlib.md5(f'{alert_id}{datetime.now().isoformat()}'.encode()).hexdigest()[:8].upper()}"
    )

    metadata = {
        "doc_id": doc_id,
        "alert_id": alert_id,
        "title": title,
        "severity": severity,
        "human_decision": human_action,
        "analyst_id": analyst_id,
        "analyst_notes": analyst_notes,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "mitre_techniques": technique_str,
        "source_ip": source_ip,
        "ai_recommended_action": ai_recommended_action,
        "learned_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist to ChromaDB (human_decisions_memory collection)
    doc = store.insert("learned_decisions", doc_id, content, metadata)

    # Track accuracy
    _track_accuracy(
        decision_id=alert_id,
        human_decision=human_action,
        ai_recommended="approve",  # AI always recommends action
    )

    rag_size = store.count("learned_decisions")
    logger.info(
        "Adaptive RAG: learned from alert '%s' (human=%s). RAG memory now has %d learned decisions.",
        alert_id, human_action, rag_size,
    )

    return {
        "doc_id": doc_id,
        "decision_id": alert_id,
        "human_decision": human_action,
        "rag_memory_size": rag_size,
        "message": f"Decision for alert '{title}' embedded into RAG memory. "
        f"AI will recall this on similar alerts.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2. LEGACY LEARNING FUNCTION (kept for backward compatibility)
# ══════════════════════════════════════════════════════════════════════════════


def learn_from_human_decision(
    decision_id: str,
    alert_context: dict[str, Any],
    ai_recommendation: str,
    ai_recommended_action: str,
    human_decision: str,
    human_notes: str,
    analyst_id: str,
    mitre_techniques: list[str] | None = None,
    risk_score: float = 0.0,
    risk_level: str = "medium",
) -> dict[str, Any]:
    """Legacy wrapper — delegates to learn_from_human."""
    decision_package = {
        "alert_id": decision_id,
        "title": alert_context.get("title", alert_context.get("description", decision_id)),
        "description": alert_context.get("description", str(alert_context)),
        "severity": alert_context.get("severity", "medium"),
        "mitre_techniques": mitre_techniques or [],
        "source_ip": alert_context.get("src_ip", "unknown"),
        "ai_recommendation": ai_recommendation,
        "ai_recommended_action": ai_recommended_action,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "analyst_id": analyst_id,
    }
    human_action = (
        "approved" if human_decision == "approve"
        else "rejected" if human_decision == "reject"
        else "modified"
    )
    return learn_from_human(
        decision_package=decision_package,
        human_action=human_action,
        analyst_notes=human_notes,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3. THE RECALL FUNCTION
# ══════════════════════════════════════════════════════════════════════════════


def inject_rag_context(
    alert_description: str,
    src_ip: str = "",
    mitre_techniques: list[str] | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    """
    Queries the human_decisions_memory ChromaDB collection for similar past incidents.

    Returns a structured context dict that the Master Brain uses to build
    its "Historical Memory" prompt section.

    Called BEFORE the Master Brain makes its final recommendation.
    """
    store = get_vector_store()

    # Build a rich query that ChromaDB will match semantically
    query_parts = [alert_description]
    if src_ip:
        query_parts.append(f"Source IP involved: {src_ip}")
    if mitre_techniques:
        query_parts.append(f"MITRE ATT&CK techniques detected: {', '.join(mitre_techniques)}")
    query = " | ".join(query_parts)

    similar = store.search("learned_decisions", query, top_k=top_k)

    if not similar:
        logger.info(
            "RAG recall: no similar past decisions for '%s'",
            alert_description[:60],
        )
        return {
            "has_context": False,
            "similar_decisions": [],
            "message": "No similar past decisions found in RAG memory.",
            "rag_memory_size": store.count("learned_decisions"),
        }

    # Build human-readable summaries for prompt injection
    summaries = []
    for d in similar:
        meta = d.get("metadata", {})
        human_decision = meta.get("human_decision", "unknown")
        notes = meta.get("analyst_notes", "No notes provided")
        title = meta.get("title", meta.get("alert_id", "Unknown"))
        decision_id = meta.get("alert_id", d["id"])

        summaries.append({
            "alert_id": decision_id,
            "title": title,
            "human_decision": human_decision,
            "analyst_notes": notes,
            "similarity_score": d.get("score", 0),
            "risk_score": meta.get("risk_score", "N/A"),
            "full_content": d.get("content", "")[:300],
        })

    context = {
        "has_context": True,
        "similar_decisions": summaries,
        "raw_results": similar,  # keep for the legacy prompt builder
        "message": f"Found {len(similar)} similar past decisions in RAG memory.",
        "rag_memory_size": store.count("learned_decisions"),
    }

    logger.info(
        "RAG recall: injected %d similar past decisions for query '%s'",
        len(similar), query[:80],
    )

    return context


def format_rag_context_for_prompt(rag_context: dict[str, Any]) -> str:
    """
    Generate the exact "Historical Memory" section to inject into the Master Brain prompt.

    Example output:
        --- Historical Memory (RAG) ---
        In 3 similar past incidents, the human analyst:
          - REJECTED the block action because: "False positive — legitimate admin activity"
          - APPROVED the isolation action because: "Confirmed ransomware behavior"
          - MODIFIED the action because: "Block port 445 instead of full isolation"

        Consider these human precedents before making your recommendation.
    """
    if not rag_context.get("has_context"):
        return "\n--- Historical Memory (RAG): No similar past incidents found. ---"

    raw = rag_context.get("raw_results", rag_context.get("similar_decisions", []))

    human_decisions_lines = []
    human_decisions_map = {"approved": "APPROVED", "rejected": "REJECTED", "modified": "MODIFIED"}

    for d in raw:
        meta = d.get("metadata", d)  # support both raw_result (nested) and summary (flat)
        hd = meta.get("human_decision", "unknown")
        notes = meta.get("analyst_notes", "No notes")
        decision_label = human_decisions_map.get(hd, hd.upper())
        action = meta.get("ai_recommended_action", "the action")
        alert_title = meta.get("title", meta.get("alert_id", "Unknown"))
        human_decisions_lines.append(
            f"  - {decision_label} {action} for '{alert_title}' "
            f"because: \"{notes}\""
        )

    count = len(human_decisions_lines)

    lines = [
        "",
        "--- Historical Memory (RAG): Similar Past Incidents ---",
        f"In {count} similar past {'incident' if count == 1 else 'incidents'}, "
        f"the human analyst{'s' if count == 1 else ''} decided:",
        *human_decisions_lines,
        "",
        "Consider these human precedents before making your recommendation.",
        "--------------------------------------------------------------",
    ]

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 4. ACCURACY TRACKING
# ══════════════════════════════════════════════════════════════════════════════


def _track_accuracy(decision_id: str, human_decision: str, ai_recommended: str) -> None:
    """Record a decision for trend analysis."""
    human_approved = human_decision in ("approved", "approve")
    ai_approved = ai_recommended in ("approve", "APPROVED")
    match = human_approved == ai_approved

    _ACCURACY_LOG.append({
        "decision_id": decision_id,
        "ai_recommended": ai_recommended,
        "human_decided": human_decision,
        "matched": match if human_decision in ("approved", "rejected", "approve", "reject") else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def get_accuracy_trend() -> dict[str, Any]:
    """Compute AI accuracy trend over time."""
    total = len(_ACCURACY_LOG)
    if total == 0:
        return {
            "total_decisions": 0, "matches": 0, "mismatches": 0,
            "accuracy_pct": 100.0, "trend": "no_data", "recent": [],
        }

    matches = sum(1 for e in _ACCURACY_LOG if e.get("matched") is True)
    mismatches = sum(1 for e in _ACCURACY_LOG if e.get("matched") is False)
    accuracy = (matches / max(total, 1)) * 100.0

    recent5 = _ACCURACY_LOG[-5:] if len(_ACCURACY_LOG) >= 5 else _ACCURACY_LOG
    recent_matches = sum(1 for e in recent5 if e.get("matched") is True)
    recent_accuracy = (recent_matches / max(len(recent5), 1)) * 100.0

    if recent_accuracy > accuracy + 5:
        trend = "improving"
    elif recent_accuracy < accuracy - 5:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "total_decisions": total,
        "matches": matches,
        "mismatches": mismatches,
        "undecided": total - matches - mismatches,
        "accuracy_pct": round(accuracy, 1),
        "recent_accuracy_pct": round(recent_accuracy, 1),
        "trend": trend,
        "recent": _ACCURACY_LOG[-10:],
    }
