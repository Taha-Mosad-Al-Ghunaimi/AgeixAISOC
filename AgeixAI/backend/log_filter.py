"""
AgeixAISOC — Smart Log Noise Reduction Engine.

Uses the fast_triage_llm (llama3.1) to classify raw log entries before
they reach the SIEM pipeline:

  "Normal Routine"   → Drop / cold storage  (reduces SIEM load by ~70%)
  "Suspicious Pattern" → Forward to Wazuh SIEM + trigger Master Brain

Architecture:
  1. Each raw log enters smart_log_filter(raw_log).
  2. The fast_triage_llm classifies it with a structured prompt.
  3. If LLM is unavailable, keyword-based heuristics serve as fallback.
  4. Stats (received / dropped / escalated) are tracked in memory.
  5. A REST endpoint exposes these stats at /api/stats/log-filter.
"""

import hashlib
import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger("AgeixAI.log_filter")

# ---------------------------------------------------------------------------
# In-memory stats tracker (thread-safe)
# ---------------------------------------------------------------------------

class LogFilterStats:
    """Thread-safe in-memory statistics for the log filter."""

    def __init__(self):
        self._lock = threading.Lock()
        self.total_received: int = 0
        self.total_dropped: int = 0
        self.total_escalated: int = 0
        self.total_cold_storage: int = 0
        self.llm_fallback_count: int = 0
        self._classifications: dict[str, int] = {}
        self._sources: dict[str, int] = {}

    def record(self, classification: str, source: str = "unknown") -> None:
        with self._lock:
            self.total_received += 1
            if classification == "dropped":
                self.total_dropped += 1
            elif classification == "cold_storage":
                self.total_cold_storage += 1
            elif classification == "escalated":
                self.total_escalated += 1
            self._classifications[classification] = self._classifications.get(classification, 0) + 1
            self._sources[source] = self._sources.get(source, 0) + 1

    def record_llm_fallback(self) -> None:
        with self._lock:
            self.llm_fallback_count += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            total = self.total_received
            dropped_rate = round((self.total_dropped / total * 100), 1) if total > 0 else 0.0
            escalated_rate = round((self.total_escalated / total * 100), 1) if total > 0 else 0.0
            noise_reduction_rate = round(((self.total_dropped + self.total_cold_storage) / total * 100), 1) if total > 0 else 0.0
            return {
                "total_received": total,
                "total_dropped": self.total_dropped,
                "total_cold_storage": self.total_cold_storage,
                "total_escalated": self.total_escalated,
                "dropped_rate_pct": dropped_rate,
                "escalated_rate_pct": escalated_rate,
                "noise_reduction_rate_pct": noise_reduction_rate,
                "llm_fallback_count": self.llm_fallback_count,
                "classifications_breakdown": dict(self._classifications),
                "sources_breakdown": dict(self._sources),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def reset(self) -> None:
        with self._lock:
            self.total_received = 0
            self.total_dropped = 0
            self.total_escalated = 0
            self.total_cold_storage = 0
            self.llm_fallback_count = 0
            self._classifications.clear()
            self._sources.clear()


STATS = LogFilterStats()


# ---------------------------------------------------------------------------
# LLM classification
# ---------------------------------------------------------------------------

def _classify_with_llm(raw_log_text: str) -> str | None:
    """
    Attempt to classify the raw log using the fast_triage_llm (llama3.1).

    Returns one of: "escalated", "dropped", "cold_storage", or None on failure.
    """
    try:
        from llm_config import get_fast_triage_llm

        llm = get_fast_triage_llm()
        if not llm:
            return None

        prompt = (
            "You are a SOC log triage classifier. Your job is to classify a single raw log entry.\n\n"
            "Rules:\n"
            "  - 'escalated' — Log contains indicators of compromise, attack patterns, "
            "credentials dumping, lateral movement, malware execution, C2 beaconing, "
            "privilege escalation, ransomware, data exfiltration, or brute force.\n"
            "  - 'dropped' — Log is normal routine traffic: benign HTTP 200, DNS queries to "
            "legitimate CDNs, successful auth from known user, system heartbeat, "
            "scheduled task success, routine patch check, metric report, health check.\n"
            "  - 'cold_storage' — Log is routine audit/housekeeping: log rotation, "
            "backup completion, index maintenance, DNS cache flush, time sync, "
            "NTP update, service start/stop that is expected, config validation.\n\n"
            "IMPORTANT: Respond with ONLY a single word: 'escalated', 'dropped', or 'cold_storage'. "
            "No explanation, no punctuation, no markdown.\n\n"
            f"Log entry:\n{raw_log_text[:2000]}"
        )

        response = llm.invoke(prompt)
        raw = response.strip().lower()
        # Extract the first word if the LLM gave extra text
        first_word = raw.split()[0] if raw.split() else ""
        if first_word in ("escalated", "dropped", "cold_storage"):
            logger.debug("LLM classification: %s", first_word)
            return first_word

        logger.warning("LLM returned unrecognized classification: '%s' — falling back", raw[:60])
        return None

    except Exception as exc:
        logger.warning("LLM classification failed: %s — falling back to keyword heuristic", exc)
        return None


# ---------------------------------------------------------------------------
# Keyword-based fallback classifier
# ---------------------------------------------------------------------------

# High-signal keywords that indicate suspicious activity
SUSPICIOUS_PATTERNS: list[re.Pattern] = [
    re.compile(r, re.IGNORECASE)
    for r in [
        # Credential access
        r"lsass", r"mimikatz", r"secretsdump", r"sam\.dmp", r"procdump",
        r"password.*dump", r"credentials.*access",
        # Execution
        r"powershell.*-enc", r"powershell.*-e\s", r"wscript", r"cscript",
        r"rundll32.*javascript", r"mshta", r"regsvr32",
        # Persistence
        r"scheduled.*task.*malicious", r"run.*key.*modified", r"startup.*folder",
        r"service.*install.*unknown",
        # Lateral movement
        r"psexec", r"wmic.*process", r"winrm", r"smb.*exec", r"lateral",
        # Defense evasion
        r"defender.*disabled", r"firewall.*stopped", r"eventlog.*cleared",
        r"timestomp", r"binary.*padded",
        # C2 / exfiltration
        r"c2.*beacon", r"beacon.*detected", r"dns.*tunnel", r"data.*exfil",
        r"reverse.*shell", r"outbound.*unknown.*ip", r"tor.*connection",
        # Ransomware / destruction
        r"ransomware", r"encrypt.*file", r"shadow.*delete", r"vssadmin",
        r"bootkit", r"mbr.*modify",
        # Reconnaissance
        r"port.*scan", r"enumeration", r"reconnaissance", r"whoami.*/all",
        r"nltest", r"net.*user.*/domain",
    ]
]

ROUTINE_PATTERNS: list[re.Pattern] = [
    re.compile(r, re.IGNORECASE)
    for r in [
        r"http.*200", r"status.*ok", r"health.*check", r"heartbeat",
        r"scheduled.*task.*success", r"patch.*complete", r"backup.*success",
        r"log.*rotation", r"ntp.*sync", r"time.*update", r"dns.*cache.*flush",
        r"index.*rebuild", r"service.*started.*expected", r"config.*validation",
        r"metric.*report", r"keepalive", r"session.*timeout", r"connection.*closed.*normal",
        r"user.*logout", r"password.*expir", r"certificate.*renewal",
    ]
]


def _classify_with_keywords(raw_log_text: str) -> str:
    """Keyword-based fallback classification. Faster and always available."""
    text = raw_log_text[:2000]

    # Check suspicious patterns first (safety-first approach)
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(text):
            logger.debug("Keyword fallback: SUSPICIOUS match '%s'", pattern.pattern[:40])
            return "escalated"

    # Check routine patterns
    for pattern in ROUTINE_PATTERNS:
        if pattern.search(text):
            logger.debug("Keyword fallback: ROUTINE match '%s'", pattern.pattern[:40])
            return "dropped"

    # Default: cold storage for anything unclassifiable
    return "cold_storage"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

Classification = Literal["escalated", "dropped", "cold_storage"]


def smart_log_filter(raw_log: dict[str, Any] | str) -> Classification:
    """
    Smart Log Noise Reduction Filter.

    Intercepts a raw log entry and classifies it:
      - 'escalated'     → forward to SIEM + Master Brain
      - 'dropped'       → discard (identified as benign routine)
      - 'cold_storage'  → archive for compliance, no SIEM load

    Uses the fast_triage_llm (llama3.1) for classification if available,
    with keyword-based heuristics as a zero-cost fallback.

    Parameters
    ----------
    raw_log : dict or str
        The raw log entry. If dict, it's JSON-serialized for the prompt.

    Returns
    -------
    str — one of "escalated", "dropped", "cold_storage"
    """
    # Normalize log to text
    if isinstance(raw_log, dict):
        log_text = json.dumps(raw_log, default=str)
    else:
        log_text = str(raw_log)

    # Extract a source label for stats
    source = "unknown"
    if isinstance(raw_log, dict):
        source = raw_log.get("source", raw_log.get("agent_name", raw_log.get("host", "unknown")))

    # Try LLM first
    classification = _classify_with_llm(log_text)

    if classification is None:
        # LLM unavailable — use keyword fallback
        STATS.record_llm_fallback()
        classification = _classify_with_keywords(log_text)
        logger.info("smart_log_filter: hash=%s source=%s → %s (keyword fallback)",
                     hashlib.md5(log_text[:128].encode()).hexdigest()[:8], source, classification)
    else:
        logger.info("smart_log_filter: hash=%s source=%s → %s (LLM)",
                     hashlib.md5(log_text[:128].encode()).hexdigest()[:8], source, classification)

    # Record stats
    mapping = {"escalated": "escalated", "dropped": "dropped", "cold_storage": "cold_storage"}
    STATS.record(mapping.get(classification, "dropped"), source)

    return classification


# ---------------------------------------------------------------------------
# Convenience: batch processing
# ---------------------------------------------------------------------------

def filter_log_batch(logs: list[dict[str, Any] | str]) -> tuple[list[dict[str, Any] | str], list[dict[str, Any] | str], list[dict[str, Any] | str]]:
    """
    Process a batch of logs through smart_log_filter.

    Returns (escalated, dropped, cold_storage) lists for downstream processing.
    """
    escalated: list[dict[str, Any] | str] = []
    dropped: list[dict[str, Any] | str] = []
    cold_storage: list[dict[str, Any] | str] = []

    for log in logs:
        result = smart_log_filter(log)
        if result == "escalated":
            escalated.append(log)
        elif result == "dropped":
            dropped.append(log)
        else:
            cold_storage.append(log)

    logger.info(
        "Batch filter: %d logs → %d escalated, %d dropped, %d cold_storage (reduction: %.1f%%)",
        len(logs), len(escalated), len(dropped), len(cold_storage),
        ((len(dropped) + len(cold_storage)) / len(logs) * 100) if logs else 0,
    )
    return escalated, dropped, cold_storage
