"""
AgeixAISOC — Adaptive Response Strategies via Reinforcement Learning (RL).

Every time a human analyst APPROVEs or REJECTs an AI decision, this module
logs the state (threat context, TTPs, AI recommendation, human decision)
and adjusts a confidence weight for the associated TTPs.

  ┌──────────────┐     ┌────────────────────┐     ┌──────────────┐
  │ AI Decision  │────▶│ Adaptive Learner   │────▶│ Weight Update │
  │ (TTP + Score)│     │ (RL Reward Func)   │     │ (+Δ / -Δ)     │
  └──────────────┘     └────────────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ Feedback Log │
                     │ (Immutable)  │
                     └──────────────┘
"""

import math
import random
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# TTP Confidence Weights
# ---------------------------------------------------------------------------
# Each MITRE ATT&CK technique ID maps to a float confidence weight [0, 100].
# These weights are adjusted by human feedback.

_TTP_WEIGHTS: dict[str, float] = {
    # Initial Access
    "T1190": 75.0, "T1133": 70.0, "T1078": 65.0,
    # Execution
    "T1059": 72.0, "T1204": 68.0,
    # Persistence
    "T1505": 60.0, "T1547": 65.0,
    # Privilege Escalation
    "T1548": 62.0, "T1068": 70.0,
    # Defense Evasion
    "T1562": 58.0,
    # Credential Access
    "T1003": 80.0, "T1555": 72.0, "T1110": 65.0,
    # Discovery
    "T1087": 60.0, "T1069": 55.0, "T1016": 58.0,
    # Lateral Movement
    "T1021": 74.0, "T1570": 68.0,
    # Collection
    "T1114": 66.0, "T1005": 70.0,
    # Command & Control
    "T1071": 76.0, "T1572": 72.0,
    # Exfiltration
    "T1041": 68.0, "T1567": 62.0,
    # Impact
    "T1486": 85.0, "T1490": 78.0, "T1485": 72.0,
}

# ---------------------------------------------------------------------------
# Feedback Log (immutable in-memory chain)
# ---------------------------------------------------------------------------

class FeedbackEntry:
    def __init__(
        self,
        decision_id: str,
        threat_context: str,
        ai_recommendation: str,
        ai_confidence: float,
        human_decision: str,        # "approved" | "rejected"
        ttp_ids: list[str],
        risk_score: float,
        previous_weight: float,
        new_weight: float,
        weight_delta: float,
    ):
        self.id = f"FB-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        self.decision_id = decision_id
        self.threat_context = threat_context
        self.ai_recommendation = ai_recommendation
        self.ai_confidence = ai_confidence
        self.human_decision = human_decision
        self.ttp_ids = ttp_ids
        self.risk_score = risk_score
        self.previous_weight = previous_weight
        self.new_weight = new_weight
        self.weight_delta = weight_delta
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "threat_context": self.threat_context,
            "ai_recommendation": self.ai_recommendation,
            "ai_confidence": self.ai_confidence,
            "human_decision": self.human_decision,
            "ttp_ids": self.ttp_ids,
            "risk_score": self.risk_score,
            "previous_weight": round(self.previous_weight, 1),
            "new_weight": round(self.new_weight, 1),
            "weight_delta": round(self.weight_delta, 2),
            "timestamp": self.timestamp,
        }


_FEEDBACK_LOG: list[FeedbackEntry] = []

# ---------------------------------------------------------------------------
# RL Reward Function
# ---------------------------------------------------------------------------

def _rl_reward(was_approved: bool, current_confidence: float) -> float:
    """
    Mock RL reward signal.

    - If human APPROVED: positive reward proportional to confidence.
      Higher confidence approval → smaller reward (expected).
      Lower confidence approval → larger reward (model learned something new).
    - If human REJECTED: negative reward proportional to confidence.
      Higher confidence rejection → larger penalty (model was overconfident).
    """
    if was_approved:
        # Confidence 10 → reward ~+0.90, Confidence 95 → reward ~+0.05
        return max(0.02, 1.0 - (current_confidence / 100.0))
    else:
        # Confidence 10 → penalty ~-0.10, Confidence 95 → penalty ~-0.95
        return -(current_confidence / 100.0)


# ---------------------------------------------------------------------------
# Core adaptive learning function
# ---------------------------------------------------------------------------

def apply_feedback(
    decision_id: str,
    threat_context: str,
    ai_recommendation: str,
    ai_confidence: float,
    human_decision: str,
    ttp_ids: list[str] | None = None,
    risk_score: float = 50.0,
) -> dict[str, Any]:
    """
    Called every time a human approves or rejects an AI decision.

    Steps:
    1. Look up current weight for each TTP in the decision.
    2. Compute RL reward based on human decision.
    3. Adjust weights: weight += reward * learning_rate.
    4. Log the feedback entry.
    5. Return the weight change summary.
    """
    if ttp_ids is None:
        ttp_ids = list(_TTP_WEIGHTS.keys())[:2]

    was_approved = human_decision == "approved"
    learning_rate = 0.15

    weighted_prev = 0.0
    weighted_new = 0.0
    weighted_delta = 0.0
    count = 0

    for ttp in ttp_ids:
        if ttp not in _TTP_WEIGHTS:
            continue

        prev = _TTP_WEIGHTS[ttp]
        reward = _rl_reward(was_approved, prev)

        # Apply learning rate and clip to [0, 100]
        adjustment = reward * learning_rate * 100.0
        new = max(0.0, min(100.0, prev + adjustment))
        _TTP_WEIGHTS[ttp] = new

        delta = new - prev
        weighted_prev += prev
        weighted_new += new
        weighted_delta += delta
        count += 1

    avg_prev = weighted_prev / max(count, 1)
    avg_new = weighted_new / max(count, 1)
    avg_delta = weighted_delta / max(count, 1)

    entry = FeedbackEntry(
        decision_id=decision_id,
        threat_context=threat_context,
        ai_recommendation=ai_recommendation,
        ai_confidence=ai_confidence,
        human_decision=human_decision,
        ttp_ids=ttp_ids,
        risk_score=risk_score,
        previous_weight=avg_prev,
        new_weight=avg_new,
        weight_delta=avg_delta,
    )
    _FEEDBACK_LOG.append(entry)

    return {
        "feedback_id": entry.id,
        "ttp_ids": ttp_ids,
        "avg_weight_before": round(avg_prev, 1),
        "avg_weight_after": round(avg_new, 1),
        "avg_delta": round(avg_delta, 2),
        "reward_signal": round(_rl_reward(was_approved, avg_prev), 3),
        "learning_rate": learning_rate,
    }


# ---------------------------------------------------------------------------
# Stats for /api/rl-stats
# ---------------------------------------------------------------------------

def get_rl_stats() -> dict[str, Any]:
    """
    Compute and return:
    - accuracy_score:  Simulated AI accuracy based on accumulated feedback.
    - total_feedback_events: Number of feedback entries logged.
    - learning_progress:  How much the model has adapted (0-100).
    - ttp_count: Number of tracked TTP techniques.
    - average_weight: Mean confidence across all TTPs.
    - recent_feedback: Last 20 feedback entries.
    """
    total = len(_FEEDBACK_LOG)

    # Simulated accuracy: based on approval rate + weight stability
    if total == 0:
        # Before any feedback, use baseline accuracy of ~85%
        accuracy_score = 85.0
    else:
        approvals = sum(1 for e in _FEEDBACK_LOG if e.human_decision == "approved")
        approval_rate = approvals / total
        # Start at 85 and adjust based on approval rate
        accuracy_score = 85.0 + (approval_rate - 0.5) * 30.0
        # Accuracy cannot exceed 99.5 or go below 10
        accuracy_score = max(10.0, min(99.5, accuracy_score))

    # Learning progress: how much weights have shifted from initial defaults
    initial_default = 70.0  # baseline default weight
    total_deviation = sum(abs(w - initial_default) for w in _TTP_WEIGHTS.values())
    max_possible_deviation = len(_TTP_WEIGHTS) * 70.0  # max shift per TTP: 0 or 140
    learning_progress = min(100.0, (total_deviation / max_possible_deviation) * 100.0)

    avg_weight = sum(_TTP_WEIGHTS.values()) / len(_TTP_WEIGHTS)

    recent = _FEEDBACK_LOG[-20:] if total > 0 else []

    return {
        "accuracy_score": round(accuracy_score, 1),
        "total_feedback_events": total,
        "learning_progress": round(learning_progress, 1),
        "ttp_count": len(_TTP_WEIGHTS),
        "average_weight": round(avg_weight, 1),
        "recent_feedback": [e.to_dict() for e in recent],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# TTP Lookup (used by Risk Scoring Agent)
# ---------------------------------------------------------------------------

def get_ttp_weight(ttp_id: str, default: float = 70.0) -> float:
    """Return the current learned weight for a TTP technique."""
    return _TTP_WEIGHTS.get(ttp_id, default)


def get_all_ttp_weights() -> dict[str, float]:
    """Return all current TTP weights (read-only snapshot)."""
    return dict(_TTP_WEIGHTS)


def get_feedback_log(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Paginated feedback history."""
    return [e.to_dict() for e in _FEEDBACK_LOG[offset:offset + limit]]


# ---------------------------------------------------------------------------
# Seed with mock feedback for demonstration
# ---------------------------------------------------------------------------

def _seed_mock_feedback() -> None:
    """Generate 20 mock feedback events so /api/rl-stats returns realistic data."""
    import random as _rnd
    mock_ttps = [
        ["T1190", "T1110", "T1021"],
        ["T1003", "T1059"],
        ["T1071", "T1572"],
        ["T1486", "T1490"],
        ["T1041", "T1567"],
        ["T1133", "T1078"],
        ["T1547", "T1505"],
        ["T1114", "T1005"],
        ["T1087", "T1069"],
        ["T1021", "T1570"],
        ["T1562", "T1068"],
        ["T1485", "T1071"],
        ["T1190", "T1204"],
        ["T1548", "T1059"],
        ["T1003", "T1555"],
        ["T1078", "T1133"],
        ["T1486", "T1490", "T1485"],
        ["T1021", "T1570", "T1041"],
        ["T1059", "T1562", "T1003"],
        ["T1190", "T1071", "T1486"],
    ]
    contexts = [
        "Log4j RCE exploit attempt detected on web-01. Outbound beaconing observed.",
        "Suspicious LSASS access on DC-01. Possible credential dumping.",
        "DNS tunneling detected from host 10.0.45.22 to suspicious domain.",
        "Ransomware encryption activity detected on file server FS-01.",
        "Data exfiltration via SMB to external IP 198.51.100.23.",
        "VPN brute force detected. 500+ failed logins in 10 minutes.",
        "Scheduled task creation on multiple endpoints. Potential persistence.",
        "Email harvesting via MAPI over HTTP on exchange-01.",
        "Active directory enumeration via LDAP queries from non-admin host.",
        "SMB relay attack detected between 10.0.1.45 and 10.0.2.100.",
        "Windows Defender disabled via registry modification on ws-finance-22.",
        "Ransomware recovery inhibition: shadow copies deleted on 5 servers.",
        "Malicious macro downloaded via spear-phish email attachment.",
        "UAC bypass attempt via cmstp.exe on dc-02.",
        "Browser credential theft via Chrome debugger protocol.",
        "RDP brute force from external IP targeting jump-box-01.",
        "Triple-threat: encryption + backup deletion + data exfiltration.",
        "Lateral movement via WMI from compromised workstation.",
        "Obfuscated PowerShell IEX download cradle detected in Event ID 4104.",
        "Web shell deployed on IIS server via Log4j RCE chain.",
    ]
    recommendations = [
        "Isolate host and block C2 IP at perimeter firewall.",
        "Run EDR deep scan on DC-01 and rotate krbtgt password.",
        "Add DNS sinkhole for identified domains. Review 72h of DNS logs.",
        "Enable ransomware rollback. Verify backup integrity immediately.",
        "Block SMB outbound to external IPs. Investigate data accessed.",
        "Block source IP at edge firewall. Enforce MFA for VPN access.",
        "Remove malicious scheduled tasks. Audit all endpoints for persistence.",
        "Block MAPI over HTTP from non-Exchange servers.",
        "Restrict LDAP query privileges. Monitor for further enumeration.",
        "Enable SMB signing on all endpoints. Block SMB relay protocol.",
        "Enable Windows Defender via GPO. Run full EDR scan on affected hosts.",
        "Verify backup integrity. Restore from pre-attack snapshots.",
        "Block malicious macro in Office via GPO. Train user on phishing.",
        "Apply UAC hardening GPO. Monitor for additional bypass attempts.",
        "Rotate all browser-stored credentials. Enable Credential Guard.",
        "Block source IP at edge. Review RDP access logs.",
        "Full incident response: isolate, preserve, analyze, recover.",
        "Block WMI from non-admin workstations. Investigate compromised host.",
        "Block PowerShell IEX at execution policy level. Hunt for persistence.",
        "Remove web shell. Patch Log4j. Run full web server forensics.",
    ]
    for i in range(20):
        decision_id = f"RL-SEED-{i+1:03d}"
        ttp = mock_ttps[i % len(mock_ttps)]
        approved = _rnd.random() < 0.78
        human_dec = "approved" if approved else "rejected"
        # Track the mock feedback
        # We directly update weights for seed data
        was_approved = approved
        for ttp_id in ttp:
            if ttp_id in _TTP_WEIGHTS:
                prev = _TTP_WEIGHTS[ttp_id]
                reward = _rl_reward(was_approved, prev)
                new = max(0.0, min(100.0, prev + reward * 0.15 * 100.0))
                _TTP_WEIGHTS[ttp_id] = new

        avg_prev = sum(_TTP_WEIGHTS.get(t, 70.0) for t in ttp) / len(ttp)
        avg_new = sum(_TTP_WEIGHTS.get(t, 70.0) for t in ttp) / len(ttp)

        entry = FeedbackEntry(
            decision_id=decision_id,
            threat_context=contexts[i % len(contexts)],
            ai_recommendation=recommendations[i % len(recommendations)],
            ai_confidence=_rnd.uniform(60.0, 95.0),
            human_decision=human_dec,
            ttp_ids=ttp,
            risk_score=_rnd.uniform(40.0, 95.0),
            previous_weight=avg_prev,
            new_weight=avg_new,
            weight_delta=avg_new - avg_prev,
        )
        _FEEDBACK_LOG.append(entry)


_seed_mock_feedback()
