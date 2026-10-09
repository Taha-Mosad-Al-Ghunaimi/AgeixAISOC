import random
from datetime import datetime, timezone
from typing import Any


SERVER_NAME = "wazuh-mcp"

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "get_alerts":
        count = params.get("count", 10)
        return _mock_alerts(count)
    elif action == "get_agent_status":
        agent_id = params.get("agent_id", "001")
        return _mock_agent_status(agent_id)
    elif action == "run_query":
        query = params.get("query", "")
        return _mock_query_result(query)
    elif action == "get_active_rules":
        return _mock_rules()
    elif action == "sweep_iocs":
        iocs = params.get("iocs", [])
        return _mock_ioc_sweep(iocs)
    else:
        return [{"error": f"Unknown action: {action}"}]


def _mock_alerts(count: int) -> list[dict[str, Any]]:
    alerts = []
    for i in range(count):
        alerts.append({
            "id": f"wazuh-alert-{i:04d}",
            "agent_id": f"{random.randint(1, 200):03d}",
            "agent_name": random.choice(["SRV-WEB-01", "DC-01", "WS-FINANCE-22", "SRV-DB-01", "FW-EDGE-01"]),
            "rule_id": random.choice([87104, 55001, 83292, 100101, 34301]),
            "rule_description": random.choice([
                "Login attempt from forbidden source IP",
                "Process injection detected — lsass.exe",
                "Scheduled task created by non-admin user",
                "Anomalous outbound connection to known malicious IP",
                "Registry modification — auto-start extension",
            ]),
            "severity": random.choice(["low", "medium", "high", "critical"]),
            "mitre_id": random.choice(["T1059", "T1003", "T1053", "T1071", "T1547"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    return alerts


def _mock_agent_status(agent_id: str) -> list[dict[str, Any]]:
    return [{
        "agent_id": agent_id,
        "status": random.choice(["active", "active", "active", "disconnected"]),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "os": random.choice(["Windows 11", "Ubuntu 22.04", "Windows Server 2022"]),
        "ip": f"10.0.{random.randint(1, 10)}.{random.randint(1, 255)}",
    }]


def _mock_query_result(query: str) -> list[dict[str, Any]]:
    return [{
        "query_summary": f"Processed query: {query[:50]}",
        "results_count": random.randint(1, 50),
        "sample": [{"field": "test", "value": "mock_data"}],
    }]


def _mock_rules() -> list[dict[str, Any]]:
    return [
        {"id": "87104", "name": "SSH Brute Force", "level": "10", "group": "authentication"},
        {"id": "55001", "name": "Process Injection", "level": "12", "group": "malware"},
        {"id": "83292", "name": "Scheduled Task Creation", "level": "7", "group": "sysmon"},
        {"id": "100101", "name": "C2 Beacon Detection", "level": "14", "group": "network"},
        {"id": "34301", "name": "Registry Persistence", "level": "8", "group": "windows"},
    ]


def _mock_ioc_sweep(iocs: list[str]) -> list[dict[str, Any]]:
    """Return Wazuh log matches for a list of IOCs."""
    results = []
    for ioc in iocs[:5]:  # limit to avoid over-mocking
        matches = random.randint(0, 3)
        if matches > 0:
            for m in range(matches):
                results.append({
                    "ioc": ioc,
                    "ioc_type": _classify_ioc(ioc),
                    "source": "wazuh-mcp",
                    "agent_id": f"{random.randint(1, 200):03d}",
                    "agent_name": random.choice(["SRV-WEB-01", "DC-01", "WS-FINANCE-22", "SRV-DB-01"]),
                    "rule_id": random.choice([87104, 100101, 83292]),
                    "log_line": f"Matched IOC {ioc} in Wazuh alert log #{random.randint(10000, 99999)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    return results


def _classify_ioc(value: str) -> str:
    import re
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
        return "ip"
    if re.match(r"^[0-9a-fA-F]{32,64}$", value):
        return "hash"
    if "." in value and " " not in value:
        return "domain"
    return "unknown"
