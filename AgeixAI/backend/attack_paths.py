import random
from typing import Any


NODES = [
    {"id": "attacker", "label": "Threat Actor\nC2 Infrastructure", "type": "attacker", "ip": "185.142.53.x", "os": "Linux", "compromised": False},
    {"id": "fw-01", "label": "Edge Firewall\nCisco ASA 5525", "type": "chokepoint", "ip": "10.0.0.1", "os": "ASA", "compromised": False},
    {"id": "web-01", "label": "Web Server\nApache Tomcat 9", "type": "server", "ip": "10.0.10.10", "os": "Ubuntu 22.04", "compromised": False, "vulnerabilities": ["CVE-2025-44228"]},
    {"id": "web-02", "label": "Web Server\nIIS 10", "type": "server", "ip": "10.0.10.11", "os": "Windows Server 2022", "compromised": False},
    {"id": "vlan-10-router", "label": "VLAN 10 Gateway\nL3 Switch", "type": "chokepoint", "ip": "10.0.10.1", "os": "IOS-XE", "compromised": False},
    {"id": "app-01", "label": "App Server\nNode.js API", "type": "server", "ip": "10.0.20.20", "os": "Ubuntu 22.04", "compromised": False},
    {"id": "db-01", "label": "Database\nPostgreSQL 15", "type": "server", "ip": "10.0.20.30", "os": "Ubuntu 22.04", "compromised": False},
    {"id": "vlan-20-router", "label": "VLAN 20 Gateway\nL3 Switch", "type": "chokepoint", "ip": "10.0.20.1", "os": "IOS-XE", "compromised": False},
    {"id": "ws-01", "label": "Workstation 01\nFinance Dept", "type": "endpoint", "ip": "10.0.30.50", "os": "Windows 11", "compromised": True},
    {"id": "ws-02", "label": "Workstation 02\nHR Dept", "type": "endpoint", "ip": "10.0.30.51", "os": "Windows 11", "compromised": False},
    {"id": "fs-01", "label": "File Server\nSMB Share", "type": "server", "ip": "10.0.30.60", "os": "Windows Server 2022", "compromised": False},
    {"id": "vlan-30-router", "label": "VLAN 30 Gateway\nL3 Switch", "type": "chokepoint", "ip": "10.0.30.1", "os": "IOS-XE", "compromised": False},
    {"id": "dc-01", "label": "Domain Controller\nActive Directory", "type": "dc", "ip": "10.0.40.10", "os": "Windows Server 2025", "compromised": False},
]

EDGES = [
    {"source": "attacker", "target": "fw-01", "protocol": "HTTPS", "seconds": 0},
    {"source": "fw-01", "target": "web-01", "protocol": "HTTPS", "seconds": 0},
    {"source": "fw-01", "target": "web-02", "protocol": "HTTPS", "seconds": 0},
    {"source": "web-01", "target": "vlan-10-router", "protocol": "802.1Q", "seconds": 300},
    {"source": "vlan-10-router", "target": "app-01", "protocol": "HTTP", "seconds": 600},
    {"source": "app-01", "target": "db-01", "protocol": "PostgreSQL", "seconds": 900},
    {"source": "db-01", "target": "vlan-30-router", "protocol": "802.1Q", "seconds": 1200},
    {"source": "web-01", "target": "vlan-20-router", "protocol": "802.1Q", "seconds": 600},
    {"source": "vlan-20-router", "target": "ws-01", "protocol": "RDP", "seconds": 1200},
    {"source": "ws-01", "target": "fs-01", "protocol": "SMB", "seconds": 3600},
    {"source": "ws-01", "target": "ws-02", "protocol": "SMB", "seconds": 1800},
    {"source": "fs-01", "target": "vlan-30-router", "protocol": "802.1Q", "seconds": 7200},
    {"source": "vlan-30-router", "target": "dc-01", "protocol": "LDAP", "seconds": 14400},
    {"source": "vlan-10-router", "target": "vlan-30-router", "protocol": "OSPF", "seconds": 1800},
    {"source": "app-01", "target": "vlan-20-router", "protocol": "802.1Q", "seconds": 600},
]

PATHS = [
    {"id": "path-1", "path": ["attacker", "fw-01", "web-01", "vlan-10-router", "app-01", "db-01", "vlan-30-router", "dc-01"], "probability": 0.78, "hops": 6, "risk": "critical"},
    {"id": "path-2", "path": ["attacker", "fw-01", "web-01", "vlan-20-router", "ws-01", "fs-01", "vlan-30-router", "dc-01"], "probability": 0.45, "hops": 6, "risk": "high"},
    {"id": "path-3", "path": ["attacker", "fw-01", "web-01", "vlan-20-router", "ws-01", "ws-02", "fs-01", "vlan-30-router", "dc-01"], "probability": 0.22, "hops": 8, "risk": "medium"},
]

TIMELINE = [
    {"time": "0h", "seconds": 0, "compromised": ["attacker"], "description": "Initial access via C2 infrastructure targeting edge services"},
    {"time": "1h", "seconds": 3600, "compromised": ["attacker", "fw-01", "web-01", "vlan-10-router", "app-01"], "description": "Lateral movement through DMZ into application VLAN"},
    {"time": "2h", "seconds": 7200, "compromised": ["attacker", "fw-01", "web-01", "vlan-10-router", "app-01", "db-01", "vlan-20-router", "ws-01"], "description": "Database exfiltrated; credentials captured for lateral pivot"},
    {"time": "4h", "seconds": 14400, "compromised": ["attacker", "fw-01", "web-01", "vlan-10-router", "app-01", "db-01", "vlan-20-router", "ws-01", "ws-02", "fs-01", "vlan-30-router", "dc-01"], "description": "Domain Controller compromised \u2014 full network takeover"},
]

RECOMMENDATIONS = [
    {"priority": "urgent", "action": "Deploy micro-segmentation between VLAN 10 and VLAN 20", "target": "vlan-10-router, vlan-20-router", "reason": "Currently any host in VLAN 10 can initiate connections to VLAN 20 \u2014 enables lateral movement"},
    {"priority": "urgent", "action": "Patch Log4j on web-01 (CVE-2025-44228)", "target": "web-01", "reason": "Initial compromise vector \u2014 RCE via JNDI injection"},
    {"priority": "recommended", "action": "Enforce RDP with Network Level Authentication on VLAN 20 endpoints", "target": "ws-01, ws-02", "reason": "RDP without NLA allows credential relay attacks"},
    {"priority": "recommended", "action": "Deploy EDR on Linux servers in VLAN 10", "target": "app-01, db-01", "reason": "No EDR agent installed \u2014 cannot detect post-exploitation activity"},
    {"priority": "optional", "action": "Upgrade ASA firmware on fw-01", "target": "fw-01", "reason": "Firmware is 2 versions behind \u2014 3 CVEs with public exploits"},
]


def predict_attack_paths(time_seconds: int = 14400) -> dict[str, Any]:
    compromised = []
    for slice_ in TIMELINE:
        if slice_["seconds"] <= time_seconds:
            compromised = slice_["compromised"]

    scored_paths = sorted(PATHS, key=lambda p: p["probability"], reverse=True)

    nodes = []
    for n in NODES:
        node = dict(n)
        node["compromised"] = n["id"] in compromised
        nodes.append(node)

    edges = []
    for e in EDGES:
        edge = dict(e)
        edge["active"] = e["seconds"] <= time_seconds
        edges.append(edge)

    context = "simulation"
    if time_seconds <= 60:
        context = "Initial breach detected at edge firewall"
    elif time_seconds <= 3600:
        context = "Lateral movement in progress — DMZ compromised, app VLAN at risk"
    elif time_seconds <= 7200:
        context = "Internal VLANs breached — credential harvesting detected"
    else:
        context = "Domain Controller compromised — critical infrastructure takeover imminent"

    return {
        "nodes": nodes,
        "edges": edges,
        "paths": scored_paths,
        "timeline": TIMELINE,
        "recommendations": RECOMMENDATIONS,
        "current_time_seconds": time_seconds,
        "context": context,
    }
