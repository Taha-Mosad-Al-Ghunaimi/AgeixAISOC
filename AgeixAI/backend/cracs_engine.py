"""
AgeixAISOC — CRACS (Cross-Agent Correlation System).

Correlates alerts across Wazuh SIEM, FortiGate firewall, and OSINT
feeds to identify multi-vector attack campaigns.  Produces a campaign
score and recommended SOAR actions.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger("AgeixAI.cracs")

CORRELATION_WINDOW_MINUTES = 30
CAMPAIGN_TEMPLATES = {
    "phishing_to_c2": {
        "name": "Phishing → C2 Beaconing",
        "description": "Email phishing leads to C2 beaconing detected by FortiGate",
        "severity": "critical",
        "soar_playbook": "playbook_phishing_c2_isolation",
    },
    "lateral_movement": {
        "name": "Lateral Movement Campaign",
        "description": "Initial breach followed by PsExec/WMI lateral movement",
        "severity": "critical",
        "soar_playbook": "playbook_lateral_movement_containment",
    },
    "ransomware_deployment": {
        "name": "Ransomware Deployment",
        "description": "C2 beacon → credential dumping → volume shadow copy deletion → encryption",
        "severity": "critical",
        "soar_playbook": "playbook_ransomware_containment",
    },
    "data_exfiltration": {
        "name": "Data Exfiltration",
        "description": "Large outbound data transfer to unusual external IP",
        "severity": "high",
        "soar_playbook": "playbook_data_exfil_block",
    },
    "recon_scanning": {
        "name": "Reconnaissance Scanning",
        "description": "Port scan from external IP detected by Wazuh and FortiGate",
        "severity": "medium",
        "soar_playbook": "playbook_recon_block",
    },
}


def _extract_ioc_set(alert: dict) -> set[str]:
    iocs = set()
    for key in ("src_ip", "dst_ip"):
        ip = alert.get(key, "")
        if ip:
            iocs.add(ip)
    raw = alert.get("raw_event", {})
    if isinstance(raw, dict):
        for ioc in raw.get("iocs", []):
            if isinstance(ioc, dict):
                val = ioc.get("value", "")
                if val:
                    iocs.add(val)
            elif isinstance(ioc, str):
                iocs.add(ioc)
    return iocs


def _normalize_threat_name(name: str) -> str:
    name = name.lower().strip()
    if "phish" in name or "spear" in name or "spam" in name:
        return "phishing"
    if "beacon" in name or "c2" in name or "cobalt" in name or "meterpreter" in name:
        return "c2_beacon"
    if "ransom" in name or "lockbit" in name or "encrypt" in name:
        return "ransomware"
    if "exfil" in name or "data_loss" in name or "data_send" in name:
        return "data_exfil"
    if "scan" in name or "recon" in name or "portscan" in name or "nmap" in name:
        return "recon"
    if "lateral" in name or "psexec" in name or "wmi" in name or "remote" in name:
        return "lateral_move"
    return "unknown"


def correlate_alerts(alerts: list[dict]) -> dict:
    if not alerts:
        return {
            "campaign_detected": False,
            "campaigns": [],
            "total_alerts": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    correlated = []
    seen_iocs: dict[str, list[dict]] = {}
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=CORRELATION_WINDOW_MINUTES)

    for alert in alerts:
        ts_str = alert.get("timestamp") or alert.get("_meta", {}).get("timestamp", "")
        try:
            alert_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            alert_time = now

        if alert_time < window_start:
            continue

        iocs = _extract_ioc_set(alert)
        for ioc in iocs:
            if ioc not in seen_iocs:
                seen_iocs[ioc] = []
            seen_iocs[ioc].append(alert)
            correlated.append(alert)

    campaigns = []
    matched_templates = set()

    for ioc, related in seen_iocs.items():
        if len(related) < 2:
            continue

        threat_types = [_normalize_threat_name(a.get("rule_description", "")) for a in related]
        unique_types = list(set(threat_types))

        campaign = None
        if "phishing" in unique_types and "c2_beacon" in unique_types:
            campaign = "phishing_to_c2"
        elif "recon" in unique_types and "lateral_move" in unique_types:
            campaign = "lateral_movement"
        elif "c2_beacon" in unique_types and "ransomware" in unique_types:
            campaign = "ransomware_deployment"
        elif "data_exfil" in unique_types:
            campaign = "data_exfiltration"
        elif "recon" in unique_types:
            campaign = "recon_scanning"
        elif "lateral_move" in unique_types:
            campaign = "lateral_movement"

        if campaign and campaign not in matched_templates:
            matched_templates.add(campaign)
            template = CAMPAIGN_TEMPLATES[campaign]
            risk_scores = [a.get("risk_score", 50) for a in related]
            avg_risk = sum(risk_scores) / len(risk_scores)

            campaigns.append({
                "campaign_id": f"CAMP-{hashlib.md5(campaign.encode()).hexdigest()[:8].upper()}",
                "campaign_name": template["name"],
                "description": template["description"],
                "severity": template["severity"],
                "soar_playbook": template["soar_playbook"],
                "shared_ioc": ioc,
                "correlated_alerts": len(related),
                "avg_risk_score": round(avg_risk, 1),
                "unique_threat_types": unique_types,
                "agent_sources": list(set(a.get("agent_name", "unknown") for a in related)),
                "detected_at": now.isoformat(),
            })

    return {
        "campaign_detected": len(campaigns) > 0,
        "campaigns": campaigns,
        "total_alerts": len(alerts),
        "correlated_in_window": len(correlated),
        "timestamp": now.isoformat(),
    }


def get_campaign_summary(campaign_id: str, campaigns: list[dict]) -> Optional[dict]:
    for c in campaigns:
        if c["campaign_id"] == campaign_id:
            return c
    return None
