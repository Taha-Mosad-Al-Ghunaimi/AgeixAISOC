"""
Detection Gap Feedback Loop — the self-healing mechanism of the SOC.

Sequential workflow
-------------------
1.  Red Team Agent simulates an attack (SSH Brute Force, Kerberoasting, or CVE-based exploit).
2.  System checks if Wazuh (SIEM) detected it via GET /alerts (mock call to WP1).
3.  If NO alert found (Gap Identified):
    a. AI generates a new Sigma Rule in YAML format targeting this specific MITRE technique.
    b. The Sigma rule is sent to the Pending Human Approval queue on the Dashboard.
4.  Human approves via POST /rules/approve.
5.  Backend calls POST /rules/deploy to WP1 (Wazuh) to deploy the Sigma rule.
6.  System re-runs the attack simulation to verify the gap is closed.
7.  MITRE ATT&CK coverage heatmap data is updated.
8.  Full loop runs as a background asyncio task so it never blocks the FastAPI event loop.
"""

import asyncio
import hashlib
import logging
import random
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

logger = logging.getLogger("AgeixAI.gap_loop")


class AttackType(Enum):
    """The type of attack the Red Team Agent can simulate."""
    SSH_BRUTE_FORCE = "ssh_brute_force"
    KERBEROASTING = "kerberoasting"
    CVE_BASED = "cve_based"


# ── MITRE ATT&CK Framework (14 tactics) ─────────────────────────────────────

MITRE_TACTICS: list[dict[str, Any]] = [
    {"id": "TA0043", "name": "Reconnaissance",       "coverage": 95},
    {"id": "TA0042", "name": "Resource Development",  "coverage": 88},
    {"id": "TA0001", "name": "Initial Access",        "coverage": 92},
    {"id": "TA0002", "name": "Execution",             "coverage": 96},
    {"id": "TA0003", "name": "Persistence",           "coverage": 85},
    {"id": "TA0004", "name": "Privilege Escalation",  "coverage": 78},  # lowest gap candidate
    {"id": "TA0005", "name": "Defense Evasion",       "coverage": 91},
    {"id": "TA0006", "name": "Credential Access",     "coverage": 87},
    {"id": "TA0007", "name": "Discovery",             "coverage": 94},
    {"id": "TA0008", "name": "Lateral Movement",      "coverage": 82},
    {"id": "TA0009", "name": "Collection",            "coverage": 89},
    {"id": "TA0011", "name": "Command & Control",     "coverage": 76},
    {"id": "TA0010", "name": "Exfiltration",          "coverage": 83},
    {"id": "TA0040", "name": "Impact",                "coverage": 79},
]

TACTIC_INDEX = {t["id"]: i for i, t in enumerate(MITRE_TACTICS)}

# ── CVE → MITRE Technique Mapping ───────────────────────────────────────────

CVE_TO_MITRE: dict[str, dict[str, Any]] = {
    "CVE-2025-44228": {
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "cvss": 9.8,
        "affected_software": "Apache Log4j 2.x < 2.17.1",
        "metasploit_module": "exploit/multi/http/log4j2_rce",
    },
    "CVE-2024-6387": {
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "cvss": 8.1,
        "affected_software": "OpenSSH < 9.8",
        "metasploit_module": "exploit/linux/ssh/regresshion",
    },
    "CVE-2023-23397": {
        "technique_id": "T1557.001",
        "technique_name": "LLMNR/NBT-NS Poisoning and SMB Relay",
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "cvss": 9.1,
        "affected_software": "Microsoft Outlook",
        "metasploit_module": "exploit/windows/smb/outlook_ntlm_relay",
    },
    "CVE-2026-3312": {
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "cvss": 7.5,
        "affected_software": "Internal Web Application",
        "metasploit_module": "exploit/multi/http/sqlmap_automation",
    },
    "CVE-2025-3312": {
        "technique_id": "T1021.002",
        "technique_name": "SMB/Windows Admin Shares",
        "tactic_id": "TA0008",
        "tactic_name": "Lateral Movement",
        "cvss": 7.2,
        "affected_software": "Samba 4.x / Windows SMB",
        "metasploit_module": "exploit/windows/smb/psexec",
    },
    "CVE-2025-1111": {
        "technique_id": "T1059.001",
        "technique_name": "PowerShell",
        "tactic_id": "TA0002",
        "tactic_name": "Execution",
        "cvss": 8.5,
        "affected_software": "Windows PowerShell 5.x",
        "metasploit_module": "exploit/windows/powershell/powerdump",
    },
}

# ── Mock OpenVAS scan targets ───────────────────────────────────────────────

SCAN_TARGETS = [
    {"host": "web-01", "ip": "10.0.10.10", "os": "Ubuntu 22.04", "services": ["Apache 2.4.57", "OpenSSH 8.9p1"]},
    {"host": "app-01", "ip": "10.0.20.20", "os": "Ubuntu 22.04", "services": ["Node.js 18", "PostgreSQL 15"]},
    {"host": "dc-01",  "ip": "10.0.40.10", "os": "Windows Server 2025", "services": ["AD DS", "DNS", "SMB"]},
    {"host": "ws-01",  "ip": "10.0.30.50", "os": "Windows 11", "services": ["SMB", "RDP"]},
    {"host": "fs-01",  "ip": "10.0.30.60", "os": "Windows Server 2022", "services": ["SMB"]},
]

# ── Scanner profiles — each scan picks one from below ───────────────────────

SCAN_PROFILES = [
    {"target": "web-01",  "ip": "10.0.10.10", "cve": "CVE-2025-44228", "port": 80,  "service": "Apache Tomcat"},
    {"target": "app-01",  "ip": "10.0.20.20", "cve": "CVE-2025-1111",  "port": 3000, "service": "Node.js"},
    {"target": "dc-01",   "ip": "10.0.40.10", "cve": "CVE-2025-3312",  "port": 445,  "service": "SMB"},
    {"target": "ws-01",   "ip": "10.0.30.50", "cve": "CVE-2023-23397", "port": 1433, "service": "Outlook"},
    {"target": "fs-01",   "ip": "10.0.30.60", "cve": "CVE-2025-3312",  "port": 445,  "service": "SMB"},
]

# ── Sigma rule content templates (per technique) ────────────────────────────

SIGMA_TEMPLATES: dict[str, str] = {
    "T1190": """title: Detection Gap - Exploit Public-Facing Application ({cve})
id: {rule_uuid}
status: experimental
description: >
  Auto-generated Sigma rule to close detection gap for {cve}
  ({technique_name}) on {target}. Generated by AgeixAISOC Gap Loop.
references:
  - https://nvd.nist.gov/vuln/detail/{cve}
  - https://attack.mitre.org/techniques/{technique_id}/
date: {date}
tags:
  - attack.{tactic_id}
  - attack.{technique_id}
logsource:
  category: web
  product: apache
detection:
  selection:
    c-uri|contains: '/jndi/'
    sc-status: 200
  condition: selection
falsepositives:
  - Unknown (FP analysis: {fp_risk}%)
level: high
""",
    "T1021.002": """title: Detection Gap - SMB Lateral Movement ({cve})
id: {rule_uuid}
status: experimental
description: >
  Auto-generated Sigma rule to close detection gap for {cve}
  ({technique_name}) on {target}. Generated by AgeixAISOC Gap Loop.
references:
  - https://nvd.nist.gov/vuln/detail/{cve}
  - https://attack.mitre.org/techniques/{technique_id}/
date: {date}
tags:
  - attack.{tactic_id}
  - attack.{technique_id}
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    Image|endswith: '\\psexec.exe'
    CommandLine|contains: '\\\\'
  condition: selection
falsepositives:
  - Unknown (FP analysis: {fp_risk}%)
level: high
""",
    "T1059.001": """title: Detection Gap - Malicious PowerShell ({cve})
id: {rule_uuid}
status: experimental
description: >
  Auto-generated Sigma rule to close detection gap for {cve}
  ({technique_name}) on {target}. Generated by AgeixAISOC Gap Loop.
references:
  - https://nvd.nist.gov/vuln/detail/{cve}
  - https://attack.mitre.org/techniques/{technique_id}/
date: {date}
tags:
  - attack.{tactic_id}
  - attack.{technique_id}
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4104
    ScriptBlockText|contains: 'IEX'
  condition: selection
falsepositives:
  - Unknown (FP analysis: {fp_risk}%)
level: high
""",
    "T1557.001": """title: Detection Gap - NTLM Relay ({cve})
id: {rule_uuid}
status: experimental
description: >
  Auto-generated Sigma rule to close detection gap for {cve}
  ({technique_name}) on {target}. Generated by AgeixAISOC Gap Loop.
references:
  - https://nvd.nist.gov/vuln/detail/{cve}
  - https://attack.mitre.org/techniques/{technique_id}/
date: {date}
tags:
  - attack.{tactic_id}
  - attack.{technique_id}
logsource:
  category: network_connection
  product: windows
detection:
  selection:
    Initiated: 'true'
    DestPort: 445
  condition: selection
falsepositives:
  - Unknown (FP analysis: {fp_risk}%)
level: high
""",
}

DEFAULT_SIGMA_TEMPLATE = """title: Detection Gap - Unknown Technique ({technique_id})
id: {rule_uuid}
status: experimental
description: >
  Auto-generated Sigma rule for {technique_id} ({technique_name}).
  Generated by AgeixAISOC Gap Loop for {cve} on {target}.
date: {date}
tags:
  - attack.{technique_id}
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
falsepositives:
  - Unknown (FP analysis: {fp_risk}%)
level: medium
"""

# ── In-memory state ─────────────────────────────────────────────────────────

_PENDING_SIGMA_RULES: dict[str, dict[str, Any]] = {}
_DEPLOYED_SIGMA_RULES: dict[str, dict[str, Any]] = {}
_LOOP_HISTORY: list[dict[str, Any]] = []
_COVERAGE_HISTORY: list[list[dict[str, Any]]] = []

# ── Step 1: Mock OpenVAS Scanner ────────────────────────────────────────────

def step1_vulnerability_scan() -> dict[str, Any]:
    profile = random.choice(SCAN_PROFILES)
    cve_data = CVE_TO_MITRE[profile["cve"]]
    scan_raw = f'{profile["target"]}{profile["cve"]}{random.random()}'
    return {
        "scan_id": f"OVS-{hashlib.md5(scan_raw.encode()).hexdigest()[:8].upper()}",
        "target": profile["target"],
        "ip": profile["ip"],
        "port": profile["port"],
        "service": profile["service"],
        "cve": profile["cve"],
        "cvss": cve_data["cvss"],
        "description": f"{profile['cve']} — {cve_data['technique_name']} on {profile['target']}:{profile['port']} ({profile['service']})",
    }


# ── Step 2: CVE → MITRE ATT&CK Mapping ──────────────────────────────────────

def step2_map_to_mitre(cve_id: str) -> dict[str, Any]:
    cve_data = CVE_TO_MITRE.get(cve_id)
    if not cve_data:
        return {"technique_id": "T1068", "technique_name": "Exploitation for Privilege Escalation", "tactic_id": "TA0004", "tactic_name": "Privilege Escalation"}
    return {
        "technique_id": cve_data["technique_id"],
        "technique_name": cve_data["technique_name"],
        "tactic_id": cve_data["tactic_id"],
        "tactic_name": cve_data["tactic_name"],
    }


# ── Step 3: Red Team Attack Simulation ───────────────────────────────────────

def step3_simulate_attack(scan_result: dict[str, Any]) -> dict[str, Any]:
    cve_data = CVE_TO_MITRE.get(scan_result["cve"], {})
    msf_module = cve_data.get("metasploit_module", "exploit/multi/handler")
    return {
        "simulation_id": f"MSF-{hashlib.md5(str(random.random()).encode()).hexdigest()[:8].upper()}",
        "target": scan_result["target"],
        "cve": scan_result["cve"],
        "metasploit_module": msf_module,
        "execution_result": random.choice(["SESSION_OPENED", "SESSION_OPENED", "SESSION_OPENED", "PAYLOAD_FAILED"]),
        "access_level": "SYSTEM" if random.random() > 0.3 else "USER",
        "commands_executed": [
            f"use {msf_module}",
            f"set RHOSTS {scan_result['ip']}",
            f"set RPORT {scan_result['port']}",
            "set PAYLOAD windows/x64/meterpreter/reverse_tcp",
            "exploit -j",
        ],
        "simulated_damage": f"Attacker gained {random.choice(['user', 'admin', 'SYSTEM'])} access to {scan_result['target']}. Technique: {cve_data.get('technique_name', 'unknown')}.",
    }


# ── Step 3b: SSH Brute Force Simulation (T1110.001) ──────────────────────────

SSH_BRUTE_FORCE_TARGETS = [
    {"host": "web-01", "ip": "10.0.10.10", "os": "Ubuntu 22.04", "ssh_port": 22},
    {"host": "app-01", "ip": "10.0.20.20", "os": "Ubuntu 22.04", "ssh_port": 22},
    {"host": "bastion-01", "ip": "10.0.0.10", "os": "Ubuntu 24.04", "ssh_port": 2222},
]


def simulate_ssh_brute_force() -> dict[str, Any]:
    target = random.choice(SSH_BRUTE_FORCE_TARGETS)
    usernames = ["root", "admin", "ubuntu", "deploy", "oracle", "postgres", "backup"]
    target_user = random.choice(usernames)
    password_list = ["admin123", "Password1", "root123", "Welcome1", "P@ssw0rd", "12345678", "letmein"]
    attempt_count = random.randint(50, 500)
    success = random.random() > 0.4
    return {
        "simulation_id": f"BF-{hashlib.md5(str(random.random()).encode()).hexdigest()[:8].upper()}",
        "attack_type": AttackType.SSH_BRUTE_FORCE.value,
        "technique_id": "T1110.001",
        "technique_name": "SSH Brute Force",
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "target": target["host"],
        "ip": target["ip"],
        "target_user": target_user,
        "attempts": attempt_count,
        "success": success,
        "password_used": random.choice(password_list) if success else None,
        "commands_executed": [
            f"hydra -l {target_user} -P /usr/share/wordlists/rockyou.txt ssh://{target['ip']} -t 4",
            f"medusa -u {target_user} -P /usr/share/wordlists/rockyou.txt -h {target['ip']} -M ssh",
        ],
        "simulated_damage": f"Attacker brute-forced SSH on {target['host']} as {target_user}. {'Success: shell access gained' if success else 'Failed: account locked out'}.",
    }


# ── Step 3c: Kerberoasting Simulation (T1558.003) ───────────────────────────

KERBEROASTING_TARGETS = [
    {"host": "dc-01", "ip": "10.0.40.10", "domain": "ageixai.corp", "os": "Windows Server 2025"},
    {"host": "dc-02", "ip": "10.0.40.11", "domain": "ageixai.corp", "os": "Windows Server 2022"},
]


def simulate_kerberoasting() -> dict[str, Any]:
    target = random.choice(KERBEROASTING_TARGETS)
    service_accounts = ["svc_sql", "svc_iis", "svc_backup", "svc_exchange", "svc_ldap"]
    target_account = random.choice(service_accounts)
    ticket_count = random.randint(3, 20)
    hash_cracked = random.random() > 0.5
    return {
        "simulation_id": f"KRB-{hashlib.md5(str(random.random()).encode()).hexdigest()[:8].upper()}",
        "attack_type": AttackType.KERBEROASTING.value,
        "technique_id": "T1558.003",
        "technique_name": "Kerberoasting",
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "target": target["host"],
        "ip": target["ip"],
        "domain": target["domain"],
        "service_account": target_account,
        "service_principal_name": f"{target_account}/{target['host']}.{target['domain']}",
        "tickets_extracted": ticket_count,
        "hash_cracked": hash_cracked,
        "cracked_password": "Summer2024!" if hash_cracked else None,
        "commands_executed": [
            f"python3 GetUserSPNs.py -dc-ip {target['ip']} {target['domain']}/ -request",
            "hashcat -m 13100 tickets.txt /usr/share/wordlists/rockyou.txt",
            f"impacket-secretsdump {target['domain']}/{target_account}:Summer2024!@{target['ip']}",
        ],
        "simulated_damage": f"Attacker extracted {ticket_count} Kerberos TGS tickets from {target['host']}. {'Hash cracked: domain admin access possible' if hash_cracked else 'Hash not cracked'}.",
    }


# ── Step 4: Parallel Detection Check (Wazuh + EDR + NDR) ────────────────────

WAZUH_MOCK_ACTIVE_DETECTIONS = {
    "T1190": False,
    "T1021.002": False,
    "T1059.001": True,
    "T1557.001": False,
}

EDR_MOCK_ACTIVE_DETECTIONS = {
    "T1190": False,
    "T1021.002": True,
    "T1059.001": True,
    "T1557.001": False,
}

NDR_MOCK_ACTIVE_DETECTIONS = {
    "T1190": False,
    "T1021.002": False,
    "T1059.001": False,
    "T1557.001": False,
}


def step4_check_detection(technique_id: str) -> dict[str, Any]:
    wazuh_detected = WAZUH_MOCK_ACTIVE_DETECTIONS.get(technique_id, random.choice([True, False]))
    edr_detected = EDR_MOCK_ACTIVE_DETECTIONS.get(technique_id, random.choice([True, False]))
    ndr_detected = NDR_MOCK_ACTIVE_DETECTIONS.get(technique_id, random.choice([True, False]))

    results = {
        "wazuh": {"detected": wazuh_detected, "rules_matched": ["SIGMA-001"] if wazuh_detected else [], "confidence": "high" if wazuh_detected else "none"},
        "edr":   {"detected": edr_detected,   "rules_matched": ["EDR-PROC-003"] if edr_detected else [],   "confidence": "high" if edr_detected else "none"},
        "ndr":   {"detected": ndr_detected,   "rules_matched": ["NDR-FLOW-007"] if ndr_detected else [],  "confidence": "medium" if ndr_detected else "none"},
    }

    overall_detected = wazuh_detected or edr_detected or ndr_detected
    detecting_sensors = [s for s, r in results.items() if r["detected"]]

    return {
        "overall_detected": overall_detected,
        "detecting_sensors": detecting_sensors,
        "results": results,
        "technique_id": technique_id,
    }


# ── Step 4b: Wazuh GET /alerts Mock (WP1 API) ────────────────────────────────

WAZUH_MOCK_ALERTS_DB: dict[str, list[dict[str, Any]]] = {
    "T1190": [
        {"alert_id": "WZ-001", "rule_id": 87100, "title": "Apache Log4j RCE Attempt", "timestamp": "2026-07-11T10:00:00Z", "src_ip": "10.0.10.10", "mitre_id": "T1190"},
    ],
    "T1021.002": [],
    "T1059.001": [
        {"alert_id": "WZ-002", "rule_id": 41004, "title": "PowerShell Encoded Command", "timestamp": "2026-07-11T11:00:00Z", "src_ip": "10.0.30.50", "mitre_id": "T1059.001"},
        {"alert_id": "WZ-003", "rule_id": 41005, "title": "Suspicious PowerShell Execution", "timestamp": "2026-07-11T11:05:00Z", "src_ip": "10.0.30.50", "mitre_id": "T1059.001"},
    ],
    "T1557.001": [],
    "T1110.001": [],
    "T1558.003": [],
}

WAZUH_COVERAGE_EVOLVING: dict[str, bool] = {
    "T1190": False,
    "T1021.002": False,
    "T1059.001": True,
    "T1557.001": False,
    "T1110.001": False,
    "T1558.003": False,
}


def wazuh_get_alerts(technique_id: str) -> dict[str, Any]:
    """
    Mock call to WP1 (Wazuh) GET /alerts?mitre_id={technique_id}.
    Returns any alerts Wazuh has for this technique.
    """
    alerts = WAZUH_MOCK_ALERTS_DB.get(technique_id, [])
    detected = WAZUH_COVERAGE_EVOLVING.get(technique_id, False)
    return {
        "source": "wazuh",
        "technique_id": technique_id,
        "detected": detected,
        "alert_count": len(alerts),
        "alerts": alerts,
        "message": f"Wazuh {'DETECTED' if detected else 'NO DETECTION'} for {technique_id} ({len(alerts)} alerts found)",
    }


def mark_wazuh_coverage(technique_id: str, detected: bool = True) -> None:
    """Update the Wazuh detection coverage for a technique (used after deploy)."""
    WAZUH_COVERAGE_EVOLVING[technique_id] = detected
    if detected and technique_id not in WAZUH_MOCK_ALERTS_DB:
        WAZUH_MOCK_ALERTS_DB[technique_id] = []
    if detected:
        WAZUH_MOCK_ALERTS_DB[technique_id].append({
            "alert_id": f"WZ-GAP-{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6].upper()}",
            "rule_id": random.randint(90000, 99999),
            "title": f"Gap Loop Rule triggered for {technique_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "src_ip": "10.0.0.0",
            "mitre_id": technique_id,
        })


# ── Step 5a: Generate Sigma Rule ────────────────────────────────────────────

def step5a_generate_sigma_rule(scan: dict[str, Any], mitre: dict[str, Any], fp_risk: float) -> dict[str, Any]:
    technique_id = mitre["technique_id"]
    template = SIGMA_TEMPLATES.get(technique_id, DEFAULT_SIGMA_TEMPLATE)
    rule_uuid = hashlib.md5(f"{scan['cve']}{technique_id}{datetime.now().isoformat()}".encode()).hexdigest()
    rule_uuid = f"{rule_uuid[0:8]}-{rule_uuid[8:12]}-{rule_uuid[12:16]}-{rule_uuid[16:20]}-{rule_uuid[20:32]}"

    yaml_content = template.format(
        cve=scan["cve"],
        technique_id=technique_id.replace(".", "_"),
        technique_name=mitre["technique_name"],
        tactic_id=mitre["tactic_id"],
        target=scan["target"],
        rule_uuid=rule_uuid,
        date=datetime.now().strftime("%Y/%m/%d"),
        fp_risk=fp_risk,
    )

    return {
        "rule_id": f"SIGMA-GAP-{hashlib.md5(rule_uuid.encode()).hexdigest()[:8].upper()}",
        "title": f"Detection Gap - {mitre['technique_name']} ({scan['cve']})",
        "technique_id": technique_id,
        "technique_name": mitre["technique_name"],
        "tactic_id": mitre["tactic_id"],
        "cve": scan["cve"],
        "target": scan["target"],
        "yaml": yaml_content,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Step 5b: Cross-reference historical logs for FP analysis ────────────────

MOCK_HISTORICAL_LOG_VOLUMES: dict[str, dict[str, Any]] = {
    "T1190":     {"total_events_30d": 12450, "similar_events": 342, "false_positive_candidates": 28},
    "T1021.002": {"total_events_30d": 8900,  "similar_events": 187, "false_positive_candidates": 12},
    "T1059.001": {"total_events_30d": 22300, "similar_events": 4200, "false_positive_candidates": 890},
    "T1557.001": {"total_events_30d": 3400,  "similar_events": 45,  "false_positive_candidates": 3},
}


def step5b_analyze_false_positives(technique_id: str) -> dict[str, Any]:
    stats = MOCK_HISTORICAL_LOG_VOLUMES.get(technique_id, {"total_events_30d": 10000, "similar_events": 500, "false_positive_candidates": 50})
    fp_risk = round((stats["false_positive_candidates"] / max(stats["total_events_30d"], 1)) * 100, 2)
    return {
        "technique_id": technique_id,
        "total_events_30d": stats["total_events_30d"],
        "similar_events": stats["similar_events"],
        "false_positive_candidates": stats["false_positive_candidates"],
        "fp_risk_pct": fp_risk,
        "verdict": "LOW_FP_RISK" if fp_risk < 5 else "MEDIUM_FP_RISK" if fp_risk < 15 else "HIGH_FP_RISK",
    }


# ── Coverage update helpers ─────────────────────────────────────────────────

def _compute_overall_stats(tactics: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = {"excellent": 0, "good": 0, "fair": 0, "needs_attention": 0}
    for t in tactics:
        c = t["coverage"]
        if c >= 90:       buckets["excellent"] += 1
        elif c >= 75:     buckets["good"] += 1
        elif c >= 60:     buckets["fair"] += 1
        else:             buckets["needs_attention"] += 1
    return buckets


def update_coverage(tactic_id: str, delta: int) -> dict[str, Any]:
    idx = TACTIC_INDEX.get(tactic_id)
    if idx is None:
        return {"error": f"Unknown tactic: {tactic_id}"}

    old_val = MITRE_TACTICS[idx]["coverage"]
    new_val = min(100, max(0, old_val + delta))
    MITRE_TACTICS[idx]["coverage"] = new_val

    snapshot = [dict(t) for t in MITRE_TACTICS]
    _COVERAGE_HISTORY.append(snapshot)

    return {
        "tactic_id": tactic_id,
        "tactic_name": MITRE_TACTICS[idx]["name"],
        "previous_coverage": old_val,
        "new_coverage": new_val,
        "delta": delta,
        "overall": _compute_overall_stats(MITRE_TACTICS),
    }


def get_current_coverage() -> list[dict[str, Any]]:
    return [dict(t) for t in MITRE_TACTICS]


def get_coverage_history() -> list[list[dict[str, Any]]]:
    return list(_COVERAGE_HISTORY)


def _get_tactic_id_for_technique(technique_id: str) -> str:
    for cve_id, cve_data in CVE_TO_MITRE.items():
        if cve_data["technique_id"] == technique_id:
            return cve_data["tactic_id"]
    return "TA0002"


# ── Pending rules management ────────────────────────────────────────────────

def get_pending_rules() -> list[dict[str, Any]]:
    return [r for r in _PENDING_SIGMA_RULES.values() if r["status"] == "pending"]


def get_pending_rule(rule_id: str) -> dict[str, Any] | None:
    return _PENDING_SIGMA_RULES.get(rule_id)


def approve_rule(rule_id: str, approved_by: str = "human-analyst") -> dict[str, Any]:
    rule = _PENDING_SIGMA_RULES.get(rule_id)
    if not rule:
        return {"status": "error", "message": f"Rule {rule_id} not found."}
    if rule["status"] != "pending":
        return {"status": "error", "message": f"Rule {rule_id} already {rule['status']}."}

    rule["status"] = "approved"
    rule["approved_by"] = approved_by
    rule["approved_at"] = datetime.now(timezone.utc).isoformat()
    _DEPLOYED_SIGMA_RULES[rule_id] = rule

    technique_id = rule["technique_id"]
    tactic_id = rule["tactic_id"]

    cov_update = update_coverage(tactic_id, +8)

    return {
        "status": "deployed",
        "rule_id": rule_id,
        "technique_id": technique_id,
        "technique_name": rule["technique_name"],
        "target": rule["target"],
        "yaml": rule["yaml"],
        "coverage_update": cov_update,
        "message": f"Sigma rule {rule_id} deployed to Wazuh. MITRE coverage for {cov_update['tactic_name']} improved from {cov_update['previous_coverage']}% to {cov_update['new_coverage']}%.",
    }


def reject_rule(rule_id: str, rejected_by: str = "human-analyst") -> dict[str, Any]:
    rule = _PENDING_SIGMA_RULES.get(rule_id)
    if not rule:
        return {"status": "error", "message": f"Rule {rule_id} not found."}
    rule["status"] = "rejected"
    rule["rejected_by"] = rejected_by
    rule["rejected_at"] = datetime.now(timezone.utc).isoformat()
    return {"status": "rejected", "rule_id": rule_id, "message": f"Rule {rule_id} rejected."}


# ── Step 6: Deploy Sigma rule to Wazuh (POST /rules/deploy) ──────────────────

def deploy_sigma_to_wazuh(rule_id: str) -> dict[str, Any]:
    """
    Mock call to WP1 (Wazuh) POST /rules/deploy.
    Returns deployment result and triggers coverage + Wazuh detection update.
    """
    rule = _DEPLOYED_SIGMA_RULES.get(rule_id)
    if not rule:
        rule = _PENDING_SIGMA_RULES.get(rule_id)
        if not rule or rule["status"] != "approved":
            return {"status": "error", "message": f"Rule {rule_id} not found or not approved."}

    deploy_id = f"WAZ-DPL-{hashlib.md5(f'{rule_id}{datetime.now().isoformat()}'.encode()).hexdigest()[:8].upper()}"

    technique_id = rule["technique_id"]
    tactic_id = rule["tactic_id"]

    mark_wazuh_coverage(technique_id, detected=True)
    cov_update = update_coverage(tactic_id, +5)

    rule["deploy_id"] = deploy_id
    rule["deployed_at"] = datetime.now(timezone.utc).isoformat()
    rule["status"] = "deployed"

    logger.info(
        "[DEPLOY] Rule %s deployed to Wazuh (deploy_id=%s). Coverage for %s: %s%%",
        rule_id, deploy_id, cov_update["tactic_name"], cov_update["new_coverage"],
    )

    return {
        "status": "deployed",
        "deploy_id": deploy_id,
        "rule_id": rule_id,
        "technique_id": technique_id,
        "technique_name": rule["technique_name"],
        "target": rule["target"],
        "wazuh_rule_id": f"WZ-{random.randint(90000, 99999)}",
        "coverage_update": cov_update,
        "message": f"Sigma rule {rule_id} deployed to Wazuh. Wazuh coverage enabled for {technique_id}. MITRE {cov_update['tactic_name']} coverage: {cov_update['new_coverage']}%.",
    }


# ── Step 7: Verify gap is closed ─────────────────────────────────────────────

def verify_gap_closed(rule_id: str, attack_simulation: dict[str, Any]) -> dict[str, Any]:
    """
    Re-runs the attack simulation and checks Wazuh detection to verify the gap is closed.
    Returns the verification result including whether the detection now fires.
    """
    technique_id = attack_simulation["technique_id"]

    wazuh_result = wazuh_get_alerts(technique_id)
    detection = step4_check_detection(technique_id)

    gap_closed = wazuh_result["detected"] or detection["overall_detected"]

    verification = {
        "verification_id": f"VER-{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8].upper()}",
        "rule_id": rule_id,
        "technique_id": technique_id,
        "attack_simulation": attack_simulation["simulation_id"],
        "wazuh_detected": wazuh_result["detected"],
        "sensor_detected": detection["overall_detected"],
        "detecting_sensors": detection["detecting_sensors"],
        "gap_closed": gap_closed,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "message": f"Gap {'CLOSED' if gap_closed else 'STILL OPEN'} for {technique_id}. Wazuh: {wazuh_result['detected']}, Sensors: {detection['detecting_sensors']}.",
    }

    logger.info(
        "[VERIFY] Rule %s for %s: gap_closed=%s (Wazuh=%s, sensors=%s)",
        rule_id, technique_id, gap_closed, wazuh_result["detected"], detection["detecting_sensors"],
    )

    return verification


# ── Enhanced full gap cycle: attack → detect → sigma → deploy → verify ───────

def execute_full_gap_cycle(
    attack_type: AttackType = AttackType.CVE_BASED,
) -> dict[str, Any]:
    """
    Runs the complete Detection Gap Feedback Loop:
    1. Red Team simulates an attack (SSH Brute Force, Kerberoasting, or CVE-based).
    2. Check Wazuh GET /alerts for detection.
    3. If gap identified → generate Sigma rule → queue for HITL.
    4. After human approval → deploy to Wazuh.
    5. Verify gap closed by re-running attack + detection.
    6. Update MITRE coverage heatmap.

    Returns the full cycle result with all steps.
    """
    cycle_id = f"GAP-CYCLE-{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8].upper()}"
    logger.info("[CYCLE %s] Starting Detection Gap Feedback Loop (attack_type=%s)", cycle_id, attack_type.value)

    # ── Step 1: Red Team Attack Simulation ──────────────────────────────────
    if attack_type == AttackType.SSH_BRUTE_FORCE:
        attack = simulate_ssh_brute_force()
        logger.info("[CYCLE %s] Step 1: SSH Brute Force on %s (%s attempts)", cycle_id, attack["target"], attack["attempts"])
    elif attack_type == AttackType.KERBEROASTING:
        attack = simulate_kerberoasting()
        logger.info("[CYCLE %s] Step 1: Kerberoasting on %s (%s tickets)", cycle_id, attack["target"], attack["tickets_extracted"])
    else:
        scan = step1_vulnerability_scan()
        mitre = step2_map_to_mitre(scan["cve"])
        sim = step3_simulate_attack(scan)
        attack = {**sim, "technique_id": mitre["technique_id"], "technique_name": mitre["technique_name"],
                  "tactic_id": mitre["tactic_id"], "tactic_name": mitre["tactic_name"],
                  "cve": scan["cve"], "target": scan["target"]}
        logger.info("[CYCLE %s] Step 1: CVE-based attack %s on %s", cycle_id, scan["cve"], scan["target"])

    technique_id = attack["technique_id"]

    # ── Step 2: Check Wazuh GET /alerts ─────────────────────────────────────
    wazuh_check = wazuh_get_alerts(technique_id)
    detection = step4_check_detection(technique_id)
    gap_identified = not wazuh_check["detected"] and not detection["overall_detected"]
    logger.info("[CYCLE %s] Step 2: Wazuh /alerts?mitre_id=%s → detected=%s", cycle_id, technique_id, wazuh_check["detected"])

    cycle_result: dict[str, Any] = {
        "cycle_id": cycle_id,
        "attack_type": attack_type.value,
        "attack_simulation": attack,
        "wazuh_check": wazuh_check,
        "detection_check": detection,
        "gap_identified": gap_identified,
        "sigma_rule": None,
        "approval": None,
        "deployment": None,
        "verification": None,
        "coverage_update": None,
        "status": "completed",
    }

    if not gap_identified:
        logger.info("[CYCLE %s] Step 2: No gap — %s already detected by Wazuh/sensors", cycle_id, technique_id)
        _LOOP_HISTORY.append(cycle_result)
        return cycle_result

    # ── Step 3a: Generate Sigma Rule + FP Analysis ──────────────────────────
    logger.info("[CYCLE %s] Step 3: GAP IDENTIFIED for %s — generating Sigma rule...", cycle_id, technique_id)
    fp_result = step5b_analyze_false_positives(technique_id)
    sigma_rule = step5a_generate_sigma_rule(
        {"cve": attack.get("cve", "CVE-0000-0000"), "target": attack["target"]},
        {"technique_id": technique_id, "technique_name": attack["technique_name"],
         "tactic_id": attack.get("tactic_id", "TA0006"), "tactic_name": attack.get("tactic_name", "Credential Access")},
        fp_result["fp_risk_pct"],
    )
    sigma_rule["status"] = "pending"
    sigma_rule["loop_id"] = cycle_id
    sigma_rule["attack_type"] = attack_type.value

    _PENDING_SIGMA_RULES[sigma_rule["rule_id"]] = sigma_rule
    cycle_result["sigma_rule"] = sigma_rule
    cycle_result["status"] = "awaiting_approval"
    logger.info("[CYCLE %s] Step 3: Sigma rule %s queued for HITL (FP risk=%s%%)", cycle_id, sigma_rule["rule_id"], fp_result["fp_risk_pct"])

    _LOOP_HISTORY.append(cycle_result)
    return cycle_result


# ── Background asyncio task ──────────────────────────────────────────────────

_GAP_LOOP_BACKGROUND_TASK: asyncio.Task | None = None
_GAP_LOOP_INTERVAL_SECONDS = 300  # 5 minutes
_GAP_LOOP_RUNNING = False


async def _background_gap_cycle() -> None:
    """One iteration of the background gap loop — runs in an executor to avoid blocking."""
    loop = asyncio.get_running_loop()
    attack_type = random.choice(list(AttackType))
    try:
        result = await loop.run_in_executor(None, execute_full_gap_cycle, attack_type)
        if result["gap_identified"]:
            logger.info(
                "[BACKGROUND] Gap found: %s via %s — rule %s awaiting approval",
                result["attack_simulation"]["technique_id"],
                result["attack_type"],
                result["sigma_rule"]["rule_id"] if result.get("sigma_rule") else "N/A",
            )
        else:
            logger.info("[BACKGROUND] No gap for %s — already covered", result["attack_simulation"]["technique_id"])
    except Exception as exc:
        logger.exception("[BACKGROUND] Gap cycle failed: %s", exc)


async def start_background_gap_loop(interval_seconds: int = 300) -> None:
    """
    Background asyncio task that periodically runs the gap detection cycle.
    Runs every `interval_seconds` (default 5 min) without blocking the event loop.
    Call this once during FastAPI startup.
    """
    global _GAP_LOOP_BACKGROUND_TASK, _GAP_LOOP_INTERVAL_SECONDS, _GAP_LOOP_RUNNING
    _GAP_LOOP_INTERVAL_SECONDS = interval_seconds
    _GAP_LOOP_RUNNING = True

    logger.info("[BACKGROUND] Gap Feedback Loop started — interval=%ss", interval_seconds)

    async def _runner() -> None:
        while _GAP_LOOP_RUNNING:
            await asyncio.sleep(_GAP_LOOP_INTERVAL_SECONDS)
            await _background_gap_cycle()

    _GAP_LOOP_BACKGROUND_TASK = asyncio.create_task(_runner())


async def stop_background_gap_loop() -> None:
    """Gracefully stop the background gap loop."""
    global _GAP_LOOP_RUNNING
    _GAP_LOOP_RUNNING = False
    if _GAP_LOOP_BACKGROUND_TASK:
        _GAP_LOOP_BACKGROUND_TASK.cancel()
        logger.info("[BACKGROUND] Gap Feedback Loop stopped.")

def run_gap_loop() -> dict[str, Any]:
    loop_id = f"GAP-{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8].upper()}"

    # Step 1: Scan
    scan = step1_vulnerability_scan()
    logger.info("[GAP %s] Step 1: OpenVAS scan — found %s on %s", loop_id, scan["cve"], scan["target"])

    # Step 2: Map CVE -> MITRE
    mitre = step2_map_to_mitre(scan["cve"])
    logger.info("[GAP %s] Step 2: CVE → MITRE %s (%s)", loop_id, mitre["technique_id"], mitre["technique_name"])

    # Step 3: Simulate attack
    simulation = step3_simulate_attack(scan)
    logger.info("[GAP %s] Step 3: Red Team sim — %s on %s result=%s", loop_id, simulation["metasploit_module"], simulation["target"], simulation["execution_result"])

    # Step 4: Check detection
    detection = step4_check_detection(mitre["technique_id"])
    logger.info("[GAP %s] Step 4: Detection check — overall_detected=%s sensors=%s", loop_id, detection["overall_detected"], detection["detecting_sensors"])

    loop_result = {
        "loop_id": loop_id,
        "scan": scan,
        "mitre_mapping": mitre,
        "simulation": simulation,
        "detection_check": detection,
        "gap_identified": not detection["overall_detected"],
        "sigma_rule": None,
        "fp_analysis": None,
        "coverage_update": None,
        "status": "completed",
    }

    # Step 5: Gap identified
    if not detection["overall_detected"]:
        logger.info("[GAP %s] Step 5: GAP IDENTIFIED for %s — generating Sigma rule...", loop_id, mitre["technique_id"])

        fp_result = step5b_analyze_false_positives(mitre["technique_id"])
        loop_result["fp_analysis"] = fp_result

        sigma_rule = step5a_generate_sigma_rule(scan, mitre, fp_result["fp_risk_pct"])
        sigma_rule["status"] = "pending"
        sigma_rule["loop_id"] = loop_id

        _PENDING_SIGMA_RULES[sigma_rule["rule_id"]] = sigma_rule
        loop_result["sigma_rule"] = sigma_rule
        loop_result["status"] = "awaiting_approval"

        logger.info("[GAP %s] Sigma rule %s generated and sent to HITL (FP risk: %s%%)", loop_id, sigma_rule["rule_id"], fp_result["fp_risk_pct"])
    else:
        logger.info("[GAP %s] No gap — technique %s is already detected by %s", loop_id, mitre["technique_id"], detection["detecting_sensors"])

    _LOOP_HISTORY.append(loop_result)
    return loop_result


def get_loop_history(limit: int = 20) -> list[dict[str, Any]]:
    return list(_LOOP_HISTORY[-limit:])


def get_gap_stats() -> dict[str, Any]:
    total = len(_LOOP_HISTORY)
    gaps = sum(1 for l in _LOOP_HISTORY if l["gap_identified"])
    deployed = len(_DEPLOYED_SIGMA_RULES)
    pending = len(get_pending_rules())
    return {
        "total_loops": total,
        "gaps_identified": gaps,
        "gaps_closed": deployed,
        "pending_rules": pending,
        "current_coverage": _compute_overall_stats(MITRE_TACTICS),
    }
