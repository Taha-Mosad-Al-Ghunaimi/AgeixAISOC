"""
Proactive Cross-Agent Correlation Engine.

Continuously listens to the Hive-Mind Shared State and applies a set
of predefined correlation rules to detect causal links between
findings from different agents.

Each correlation rule is a function that takes the full beehive state
and returns a list of Correlation objects if a match is found.

Background asyncio task runs every few seconds to scan for new patterns.
"""

import asyncio
import hashlib
import logging
import random
from datetime import datetime, timezone
from typing import Any, Callable

from beehive import beehive

logger = logging.getLogger("AgeixAI.correlation_engine")


# ── Correlation model ───────────────────────────────────────────────────────

class Correlation:
    def __init__(
        self,
        rule_id: str,
        title: str,
        narrative: str,
        severity: str,
        agents_involved: list[str],
        techniques: list[str],
        recommendation: str,
        source_data: dict[str, Any] | None = None,
    ):
        self.correlation_id = f"CORR-{hashlib.md5(f'{rule_id}{datetime.now().isoformat()}'.encode()).hexdigest()[:8].upper()}"
        self.rule_id = rule_id
        self.title = title
        self.narrative = narrative
        self.severity = severity
        self.agents_involved = agents_involved
        self.techniques = techniques
        self.recommendation = recommendation
        self.source_data = source_data or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.resolved = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "rule_id": self.rule_id,
            "title": self.title,
            "narrative": self.narrative,
            "severity": self.severity,
            "agents_involved": self.agents_involved,
            "techniques": self.techniques,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
        }


# ── Correlation rule definitions ────────────────────────────────────────────

_FINDINGS_CACHE: dict[str, set[str]] = {}
_SEEN_CORRELATIONS: set[str] = set()


def _get_agent_findings(agent_name: str, keys: list[str]) -> list[Any]:
    """Extract specific findings from an agent's beehive data."""
    agent_data = beehive.read_agent(agent_name)
    results = []
    for key in keys:
        entry = agent_data.get(key)
        if entry:
            val = entry.get("value")
            if val:
                results.append(val)
    return results


def _has_any_finding(agent_name: str, keywords: list[str]) -> list[dict[str, Any]]:
    """Search an agent's hive entries for any text containing keywords."""
    agent_data = beehive.read_agent(agent_name)
    matches = []
    for key, entry in agent_data.items():
        val = entry.get("value")
        val_str = str(val).lower()
        for kw in keywords:
            if kw.lower() in val_str:
                matches.append({"key": key, "value": val, "matched_keyword": kw})
    return matches


def _find_all(pattern: str, text: str) -> bool:
    return pattern.lower() in text.lower()


def _rule_fingerprint(rule_id: str, evidence: list[str]) -> str:
    raw = rule_id + "|" + "|".join(sorted(evidence))
    return hashlib.md5(raw.encode()).hexdigest()


# ── Rule 1: SMB Exploit Match ──────────────────────────────────────────────

def rule_smb_exploit_match() -> list[Correlation]:
    """Red Team exploits Port 445 + Threat Hunter finds unusual SMB traffic."""
    red_findings = _has_any_finding("red_team", ["445", "smb", "psexec", "eternalblue"])
    hunter_findings = _has_any_finding("threat_hunter", ["smb", "445", "admin$", "enumeration"])

    if red_findings and hunter_findings:
        fp = _rule_fingerprint("SMB-001", [str(red_findings), str(hunter_findings)])
        if fp not in _SEEN_CORRELATIONS:
            _SEEN_CORRELATIONS.add(fp)
            return [Correlation(
                rule_id="SMB-001",
                title="Active Exploitation Match — SMB",
                narrative=(
                    f"Red Team successfully exploited Port 445 in lab environment. "
                    f"Simultaneously, Threat Hunter detected unusual SMB traffic in production logs. "
                    f"Master Brain correlated: lab exploit technique matches production anomaly."
                ),
                severity="critical",
                agents_involved=["red_team", "threat_hunter"],
                techniques=["T1021.002", "T1110"],
                recommendation="Immediately isolate affected hosts from SMB traffic. Block SMBv1. Enable SMB signing.",
                source_data={"red_findings": red_findings, "hunter_findings": hunter_findings},
            )]
    return []


# ── Rule 2: Credential Dumping Campaign ────────────────────────────────────

def rule_credential_dumping() -> list[Correlation]:
    """Red Team LSASS exploit + Blue Team detects LSASS access."""
    red_findings = _has_any_finding("red_team", ["lsass", "credential", "t1003", "dumping"])
    blue_findings = _has_any_finding("blue_team", ["lsass", "t1003", "4663", "credential"])

    if red_findings and blue_findings:
        fp = _rule_fingerprint("CRED-001", [str(red_findings), str(blue_findings)])
        if fp not in _SEEN_CORRELATIONS:
            _SEEN_CORRELATIONS.add(fp)
            return [Correlation(
                rule_id="CRED-001",
                title="Credential Dumping Campaign Confirmed",
                narrative=(
                    f"Red Team simulated LSASS credential dumping in lab. "
                    f"Blue Team detected anomalous LSASS access (Event 4663) on production hosts. "
                    f"Master Brain correlation: credential dumping technique is being actively tested."
                ),
                severity="high",
                agents_involved=["red_team", "blue_team"],
                techniques=["T1003.001"],
                recommendation="Enable Windows Defender Credential Guard. Audit LSASS access. Rotate KRBTGT password.",
                source_data={"red_findings": red_findings, "blue_findings": blue_findings},
            )]
    return []


# ── Rule 3: C2 Beaconing Confirmed ─────────────────────────────────────────

def rule_c2_beaconing() -> list[Correlation]:
    """Threat Hunter finds beaconing + Forensics finds C2 artifacts."""
    hunter_findings = _has_any_finding("threat_hunter", ["beacon", "c2", "command", "control", "t1071", "outbound"])
    forensics_findings = _has_any_finding("forensics", ["c2", "beacon", "t1071", "svchost", "outbound"])

    if hunter_findings and forensics_findings:
        fp = _rule_fingerprint("C2-001", [str(hunter_findings), str(forensics_findings)])
        if fp not in _SEEN_CORRELATIONS:
            _SEEN_CORRELATIONS.add(fp)
            return [Correlation(
                rule_id="C2-001",
                title="C2 Infrastructure Confirmed",
                narrative=(
                    f"Threat Hunter identified regular beaconing patterns to external IPs. "
                    f"Forensics cross-referenced and found C2 artifacts (svchost.exe outbound) on compromised hosts. "
                    f"Master Brain linkage: beaconing + artifacts = active C2 channel."
                ),
                severity="critical",
                agents_involved=["threat_hunter", "forensics"],
                techniques=["T1071.001", "T1572"],
                recommendation="Block C2 IPs at perimeter firewall. Isolate compromised hosts. Conduct full EDR scan.",
                source_data={"hunter_findings": hunter_findings, "forensics_findings": forensics_findings},
            )]
    return []


# ── Rule 4: Critical Response Path ─────────────────────────────────────────

def rule_critical_response() -> list[Correlation]:
    """Risk Scoring high score + Recommendation suggests isolation."""
    risk_data = _get_agent_findings("risk_scoring", ["risk_scores"])
    rec_data = _get_agent_findings("recommendation", ["playbooks"])

    for risk in risk_data:
        score = risk.get("final_score", 0) if isinstance(risk, dict) else 0
        risk_level = risk.get("risk_level", "") if isinstance(risk, dict) else ""
        if score >= 75 or risk_level == "critical":
            for recs in rec_data:
                if isinstance(recs, list):
                    for rec in recs:
                        action = rec.get("action", "") if isinstance(rec, dict) else ""
                        if "isolate" in action.lower() or "block" in action.lower():
                            fp = _rule_fingerprint("CRIT-001", [str(risk), str(rec)])
                            if fp not in _SEEN_CORRELATIONS:
                                _SEEN_CORRELATIONS.add(fp)
                                return [Correlation(
                                    rule_id="CRIT-001",
                                    title="Critical Response Path Triggered",
                                    narrative=(
                                        f"Risk Scoring assigned score {score}/100 ({risk_level}) to an alert. "
                                        f"Recommendation Agent suggested '{action}' — the highest-priority playbook. "
                                        f"Master Brain elevation: critical risk + immediate action = urgent response required."
                                    ),
                                    severity="critical",
                                    agents_involved=["risk_scoring", "recommendation"],
                                    techniques=[],
                                    recommendation=action,
                                    source_data={"risk_score": risk, "recommendation": rec},
                                )]
    return []


# ── Rule 5: Web Shell Detected ──────────────────────────────────────────────

def rule_web_shell() -> list[Correlation]:
    """Red Team finds web vulnerability + Threat Detection finds suspicious web requests."""
    red_findings = _has_any_finding("red_team", ["web", "http", "cve", "log4j", "apache", "tomcat", "sqli"])
    td_findings = _has_any_finding("threat_detection", ["web", "http", "payload", "shell", "rce"])

    if red_findings and td_findings:
        fp = _rule_fingerprint("WEB-001", [str(red_findings), str(td_findings)])
        if fp not in _SEEN_CORRELATIONS:
            _SEEN_CORRELATIONS.add(fp)
            return [Correlation(
                rule_id="WEB-001",
                title="Web Shell Deployment Suspected",
                narrative=(
                    f"Red Team identified exploitable web application vulnerability. "
                    f"Threat Detection flagged suspicious outbound HTTP payloads matching RCE patterns. "
                    f"Master Brain correlation: web vulnerability + suspicious payload = possible web shell."
                ),
                severity="high",
                agents_involved=["red_team", "threat_detection"],
                techniques=["T1190", "T1505.003"],
                recommendation="Review web server logs for unauthorized file uploads. Run web shell detection scanner.",
                source_data={"red_findings": red_findings, "td_findings": td_findings},
            )]
    return []


# ── Rule 6: Ransomware Pattern ──────────────────────────────────────────────

def rule_ransomware_pattern() -> list[Correlation]:
    """Forensics finds encryption + Risk Scoring high financial impact."""
    forensics_findings = _has_any_finding("forensics", ["encrypt", "ransom", "shadow", "backup"])
    risk_data = _get_agent_findings("risk_scoring", ["risk_scores"])

    for risk in risk_data:
        fin_impact = risk.get("financial_impact_usd", 0) if isinstance(risk, dict) else 0
        if forensics_findings and fin_impact > 500000:
            fp = _rule_fingerprint("RANSOM-001", [str(forensics_findings), str(fin_impact)])
            if fp not in _SEEN_CORRELATIONS:
                _SEEN_CORRELATIONS.add(fp)
                return [Correlation(
                    rule_id="RANSOM-001",
                    title="Ransomware Pattern Detected",
                    narrative=(
                        f"Forensics identified encryption-related artifacts on endpoints. "
                        f"Risk Scoring estimates financial impact of ${fin_impact:,.0f}. "
                        f"Master Brain correlation: encryption artifacts + high financial exposure = ransomware pattern."
                    ),
                    severity="critical",
                    agents_involved=["forensics", "risk_scoring"],
                    techniques=["T1486", "T1490"],
                    recommendation="Activate incident response plan. Isolate storage servers. Verify backup integrity.",
                    source_data={"forensics_findings": forensics_findings, "financial_impact": fin_impact},
                )]
    return []


# ── Rule 7: Multi-Vector Attack on Same Target ──────────────────────────────

def rule_multi_vector() -> list[Correlation]:
    """Red Team + Threat Hunter both find activity on same target host/IP."""
    red_data = _get_agent_findings("red_team", ["scan_summary"])
    hunter_data = _get_agent_findings("threat_hunter", ["hunt_results"])

    red_targets = set()
    for data in red_data:
        targets = data.get("targets_scanned", []) if isinstance(data, dict) else []
        red_targets.update(t.lower() for t in targets)

    hunter_ips = set()
    for data in hunter_data:
        findings = data if isinstance(data, list) else []
        for f in findings:
            summary = f.get("summary", "") if isinstance(f, dict) else ""
            for ip in ["10.0.", "192.168.", "172."]:
                if ip in summary:
                    hunter_ips.add(summary)

    if red_targets and hunter_ips:
        fp = _rule_fingerprint("MULTI-001", [str(red_targets), str(hunter_ips)])
        if fp not in _SEEN_CORRELATIONS:
            _SEEN_CORRELATIONS.add(fp)
            return [Correlation(
                rule_id="MULTI-001",
                title="Multi-Vector Attack on Common Target",
                narrative=(
                    f"Red Team scanned and enumerated targets: {', '.join(list(red_targets)[:3])}. "
                    f"Threat Hunter independently flagged suspicious activity on overlapping targets. "
                    f"Master Brain correlation: multiple attack vectors converging on same assets."
                ),
                severity="high",
                agents_involved=["red_team", "threat_hunter"],
                techniques=["T1046", "T1059"],
                recommendation="Prioritize patching and monitoring of converged target assets. Deploy additional detection layers.",
                source_data={"red_targets": list(red_targets), "hunter_ips": list(hunter_ips)},
            )]
    return []


# ── Rule 8: Defense Evasion Chain ───────────────────────────────────────────

def rule_defense_evasion() -> list[Correlation]:
    """Forensics finds EDR disabled + Blue Team alerts missing for a host."""
    forensics_findings = _has_any_finding("forensics", ["defender", "edr", "disabled", "registry", "t1562"])
    blue_findings = _has_any_finding("blue_team", ["wazuh", "alert"])

    if forensics_findings and not blue_findings:
        fp = _rule_fingerprint("EVADE-001", [str(forensics_findings)])
        if fp not in _SEEN_CORRELATIONS:
            _SEEN_CORRELATIONS.add(fp)
            return [Correlation(
                rule_id="EVADE-001",
                title="Defense Evasion Chain Detected",
                narrative=(
                    f"Forensics found evidence of EDR/Defender being disabled via registry. "
                    f"Blue Team has no corresponding alerts for the affected host — the blind spot is confirmed. "
                    f"Master Brain correlation: EDR tampering + missing alerts = active defense evasion."
                ),
                severity="critical",
                agents_involved=["forensics", "blue_team"],
                techniques=["T1562.001"],
                recommendation="Re-enable EDR via GPO immediately. Forensic analysis on the affected host. Investigate admin account activity.",
                source_data={"forensics_findings": forensics_findings},
            )]
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# Next-Gen XDR — Cross-Layer Correlation Rules
# ═══════════════════════════════════════════════════════════════════════════════

XDR_CRITICAL_SCORE = 95

def correlate_xdr_data(endpoint_log: dict[str, Any] | None, network_log: dict[str, Any] | None) -> dict[str, Any]:
    """
    Cross-layer XDR correlation: EDR (Endpoint) × NDR (Network) × Cloud.

    Correlation logic:
      - EDR detects 'mimikatz.exe'   AND  NDR detects abnormal SMB traffic
        → CRITICAL, MITRE T1003 (OS Credential Dumping)
      - EDR detects ransomware IOCs  AND  NDR detects C2 beaconing
        → CRITICAL, MITRE T1486 (Data Encrypted) + T1071.001 (C2)
      - Cloud IAM anomaly            AND  EDR detects lateral movement
        → CRITICAL, MITRE T1525 (Impersonation) + T1021.002 (SMB/WMI)

    Returns a correlation result dict with:
      xdr_correlation_id, title, narrative, severity, mitre_techniques,
      recommendation, requires_human_approval, risk_score, actions (list of
      {action_type, target} pairs for multi-layer SOAR response).
    """
    edr = endpoint_log or {}
    ndr = network_log or {}

    edr_events = edr.get("events", edr.get("alerts", []))
    ndr_events = ndr.get("events", ndr.get("alerts", []))
    edr_desc = str(edr.get("description", "") + " " + " ".join(str(e) for e in edr_events)).lower()
    ndr_desc = str(ndr.get("description", "") + " " + " ".join(str(e) for e in ndr_events)).lower()

    correlation_id = f"XDR-{hashlib.md5(f'{edr_desc}{ndr_desc}{datetime.now().isoformat()}'.encode()).hexdigest()[:8].upper()}"

    # ── Rule XDR-1: mimikatz + SMB → OS Credential Dumping ──────────────
    if ("mimikatz" in edr_desc or ("lsass" in edr_desc and "dump" in edr_desc)):
        if ("smb" in ndr_desc and ("445" in ndr_desc or "admin$" in ndr_desc or "abnormal" in ndr_desc)):
            src_ip = edr.get("host_ip", ndr.get("src_ip", "unknown"))
            dst_ip = ndr.get("dst_ip", edr.get("dest_ip", "unknown"))
            return {
                "xdr_correlation_id": correlation_id,
                "title": "XDR: OS Credential Dumping + Lateral Movement via SMB",
                "narrative": (
                    f"EDR detected 'mimikatz.exe' on host {src_ip} — active credential dumping (T1003). "
                    f"NDR simultaneously detected abnormal SMB traffic from {src_ip} to {dst_ip} — "
                    f"attacker is using stolen credentials for lateral movement (T1021.002). "
                    f"Cross-layer correlation: credential dumping → lateral movement chain confirmed."
                ),
                "severity": "critical",
                "mitre_techniques": [{"id": "T1003.001", "name": "LSASS Memory"}, {"id": "T1021.002", "name": "SMB/Windows Admin Shares"}],
                "recommendation": "Immediately isolate both hosts. Rotate KRBTGT password. Force domain-wide password reset.",
                "requires_human_approval": True,
                "risk_score": XDR_CRITICAL_SCORE,
                "risk_level": "critical",
                "affected_hosts": [src_ip, dst_ip],
                "actions": [
                    {"action_type": "xdr_isolate_host", "target": src_ip},
                    {"action_type": "xdr_block_ip_fortigate", "target": dst_ip},
                ],
            }

    # ── Rule XDR-2: Ransomware IOC + C2 Beaconing → Active Ransomware ───
    ransomware_kw = ["ransom", "encrypt", "shadow copy", "vssadmin", "bcdedit", "delete shadow"]
    c2_kw = ["beacon", "c2", "command", "control", "t1071", "suspicious outbound", "dns tunnel"]
    if any(kw in edr_desc for kw in ransomware_kw) and any(kw in ndr_desc for kw in c2_kw):
        src = edr.get("host_ip", "unknown")
        c2_ip = ndr.get("dst_ip", ndr.get("dest_ip", "unknown"))
        return {
            "xdr_correlation_id": correlation_id,
            "title": "XDR: Active Ransomware + C2 Communication",
            "narrative": (
                f"EDR detected ransomware indicators on {src}: file encryption, shadow copy deletion. "
                f"NDR detected C2 beaconing from {src} to {c2_ip} — attacker maintaining command channel. "
                f"Cross-layer correlation: ransomware execution with active C2 — full incident response required."
            ),
            "severity": "critical",
            "mitre_techniques": [{"id": "T1486", "name": "Data Encrypted for Impact"}, {"id": "T1071.001", "name": "Web Protocols (C2)"}],
            "recommendation": "Isolate all affected hosts immediately. Block C2 IP at perimeter. Activate IR plan. Do NOT pay ransom.",
            "requires_human_approval": True,
            "risk_score": XDR_CRITICAL_SCORE,
            "risk_level": "critical",
            "affected_hosts": [src, c2_ip],
            "actions": [
                {"action_type": "xdr_isolate_host", "target": src},
                {"action_type": "xdr_block_ip_fortigate", "target": c2_ip},
            ],
        }

    # ── Rule XDR-3: Cloud IAM Anomaly + EDR Lateral Movement → Cloud Breach
    cloud_kw = ["iam", "privilege escalation", "assumerole", "consolelogin", "unauthorized s3", "cloudtrail"]
    latmove_kw = ["wmi", "winrm", "psexec", "schtasks", "remote", "lateral", "t1021"]
    if any(kw in edr_desc for kw in latmove_kw) and any(kw in ndr_desc for kw in cloud_kw):
        user = ndr.get("user_arn", edr.get("user", "unknown"))
        host = edr.get("host_ip", "unknown")
        return {
            "xdr_correlation_id": correlation_id,
            "title": "XDR: Cloud IAM Abuse + Lateral Movement",
            "narrative": (
                f"Cloud logs show IAM anomaly for {user} — possible credential compromise. "
                f"EDR detected lateral movement from {host} using remote execution techniques. "
                f"Cross-layer correlation: cloud IAM abuse + endpoint lateral movement = hybrid cloud breach in progress."
            ),
            "severity": "critical",
            "mitre_techniques": [{"id": "T1525", "name": "Impersonation"}, {"id": "T1021.002", "name": "SMB/Windows Admin Shares"}],
            "recommendation": "Disable compromised IAM credentials immediately. Isolate affected endpoint. Initiate cloud forensics.",
            "requires_human_approval": True,
            "risk_score": XDR_CRITICAL_SCORE,
            "risk_level": "critical",
            "affected_hosts": [host, user],
            "actions": [
                {"action_type": "xdr_isolate_host", "target": host},
                {"action_type": "xdr_block_ip_fortigate", "target": ndr.get("source_ip", "0.0.0.0")},
            ],
        }

    return {"xdr_correlation_id": None, "severity": "none"}


def rule_xdr_credential_dumping_smb() -> list[Correlation]:
    """XDR Rule 1: EDR mimikatz + NDR SMB → credential dumping + lateral movement."""
    # Check the beehive for EDR-style and NDR-style findings
    td_findings = _has_any_finding("threat_detection", ["mimikatz", "lsass", "credential", "t1003"])
    hunter_findings = _has_any_finding("threat_hunter", ["smb", "445", "admin$", "lateral", "t1021"])

    if td_findings and hunter_findings:
        fp = _rule_fingerprint("XDR-CRED", [str(td_findings), str(hunter_findings)])
        if fp not in _SEEN_CORRELATIONS:
            _SEEN_CORRELATIONS.add(fp)
            return [Correlation(
                rule_id="XDR-CRED",
                title="XDR: Credential Dumping → SMB Lateral Movement",
                narrative=(
                    "Threat Detection identified credential dumping artifacts (mimikatz/LSASS). "
                    "Threat Hunter independently flagged abnormal SMB traffic on overlapping hosts. "
                    "XDR cross-layer correlation: endpoint + network = active lateral movement with stolen credentials."
                ),
                severity="critical",
                agents_involved=["threat_detection", "threat_hunter"],
                techniques=["T1003.001", "T1021.002"],
                recommendation="Isolate both source and target hosts. Rotate KRBTGT. Initiate credential audit. Required actions: xdr_isolate_host, xdr_block_ip_fortigate.",
            )]
    return []


def rule_xdr_ransomware_c2() -> list[Correlation]:
    """XDR Rule 2: EDR ransomware IOCs + NDR C2 beaconing."""
    forensics_findings = _has_any_finding("forensics", ["ransom", "encrypt", "shadow", "vssadmin"])
    hunter_findings = _has_any_finding("threat_hunter", ["beacon", "c2", "t1071", "outbound"])

    if forensics_findings and hunter_findings:
        fp = _rule_fingerprint("XDR-RANSOM", [str(forensics_findings), str(hunter_findings)])
        if fp not in _SEEN_CORRELATIONS:
            _SEEN_CORRELATIONS.add(fp)
            return [Correlation(
                rule_id="XDR-RANSOM",
                title="XDR: Ransomware Encryption + C2 Channel Active",
                narrative=(
                    "Forensics Agent detected encryption and shadow-copy deletion artifacts. "
                    "Threat Hunter detected outbound C2 beaconing from overlapping hosts. "
                    "XDR cross-layer: ransomware executing on endpoint with active command channel."
                ),
                severity="critical",
                agents_involved=["forensics", "threat_hunter"],
                techniques=["T1486", "T1071.001"],
                recommendation="Full incident response activation. Isolate hosts (xdr_isolate_host). Block C2 IP at firewall (xdr_block_ip_fortigate). Do NOT pay ransom.",
            )]
    return []


# ── All rules registry (existing + XDR) ────────────────────────────────────

CORRELATION_RULES: list[Callable[[], list[Correlation]]] = [
    rule_smb_exploit_match,
    rule_credential_dumping,
    rule_c2_beaconing,
    rule_critical_response,
    rule_web_shell,
    rule_ransomware_pattern,
    rule_multi_vector,
    rule_defense_evasion,
    rule_xdr_credential_dumping_smb,
    rule_xdr_ransomware_c2,
]

_ACTIVE_CORRELATIONS: list[Correlation] = []
_CORRELATION_HISTORY: list[Correlation] = []
_BACKGROUND_TASK: asyncio.Task | None = None
_RUNNING = False


def run_correlation_cycle() -> list[Correlation]:
    """
    Execute all correlation rules against the current beehive state.
    Returns newly discovered correlations.
    """
    new_correlations: list[Correlation] = []
    for rule in CORRELATION_RULES:
        try:
            results = rule()
            new_correlations.extend(results)
        except Exception as exc:
            logger.warning("Correlation rule %s failed: %s", rule.__name__, exc)

    for corr in new_correlations:
        _ACTIVE_CORRELATIONS.append(corr)
        _CORRELATION_HISTORY.append(corr)
        logger.info(
            "[CORRELATION] %s (%s) — agents=%s severity=%s",
            corr.title, corr.correlation_id, corr.agents_involved, corr.severity,
        )

    # Keep only last 20 active
    while len(_ACTIVE_CORRELATIONS) > 20:
        _ACTIVE_CORRELATIONS.pop(0)

    return new_correlations


def get_active_correlations() -> list[dict[str, Any]]:
    """Return non-resolved correlations sorted by severity."""
    active = [c for c in _ACTIVE_CORRELATIONS if not c.resolved]
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    active.sort(key=lambda c: severity_order.get(c.severity, 99))
    return [c.to_dict() for c in active]


def get_correlation_history(limit: int = 50) -> list[dict[str, Any]]:
    """Return historical correlations."""
    recent = _CORRELATION_HISTORY[-limit:]
    recent.reverse()
    return [c.to_dict() for c in recent]


def resolve_correlation(correlation_id: str) -> bool:
    """Mark a correlation as resolved."""
    for c in _ACTIVE_CORRELATIONS:
        if c.correlation_id == correlation_id:
            c.resolved = True
            return True
    return False


def get_correlation_stats() -> dict[str, Any]:
    total = len(_CORRELATION_HISTORY)
    active = len(get_active_correlations())
    by_severity: dict[str, int] = {}
    for c in _CORRELATION_HISTORY:
        by_severity[c.severity] = by_severity.get(c.severity, 0) + 1
    return {
        "total_correlations": total,
        "active_correlations": active,
        "by_severity": by_severity,
        "rules_active": len(CORRELATION_RULES),
    }


# ── Background asyncio task ─────────────────────────────────────────────────

async def _background_correlation_cycle() -> None:
    """Run one cycle of the correlation engine in an executor."""
    loop = asyncio.get_running_loop()
    try:
        new = await loop.run_in_executor(None, run_correlation_cycle)
        if new:
            logger.info("Background correlation cycle found %d new correlation(s)", len(new))
    except Exception as exc:
        logger.exception("Background correlation cycle failed: %s", exc)


async def start_correlation_engine(interval_seconds: int = 8) -> None:
    """
    Background asyncio task that continuously scans the beehive for
    cross-agent correlations. Runs every `interval_seconds`.
    """
    global _BACKGROUND_TASK, _RUNNING
    _RUNNING = True
    logger.info("[CORRELATION] Engine started — interval=%ss", interval_seconds)

    async def _runner() -> None:
        while _RUNNING:
            await asyncio.sleep(interval_seconds)
            await _background_correlation_cycle()

    _BACKGROUND_TASK = asyncio.create_task(_runner())


async def stop_correlation_engine() -> None:
    global _RUNNING
    _RUNNING = False
    if _BACKGROUND_TASK:
        _BACKGROUND_TASK.cancel()
        logger.info("[CORRELATION] Engine stopped.")
