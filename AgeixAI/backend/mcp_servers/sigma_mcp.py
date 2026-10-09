import random
from typing import Any


SERVER_NAME = "sigma-mcp"

SIGMA_RULES = [
    {"id": "SIGMA-001", "title": "Suspicious LSASS Access", "level": "high", "rule": "selection:\n  EventID: 4663\n  ProcessName: '*\\lsass.exe'\n  AccessMask: '0x705'", "mitre": "T1003.001"},
    {"id": "SIGMA-002", "title": "PowerShell Encoded Command", "level": "medium", "rule": "selection:\n  EventID: 4104\n  ScriptBlockText: '*-enc*'", "mitre": "T1059.001"},
    {"id": "SIGMA-003", "title": "Remote Desktop Connection from Unknown IP", "level": "high", "rule": "selection:\n  EventID: 4624\n  LogonType: 10\n  IpAddress: '!10.0.*'", "mitre": "T1021.001"},
    {"id": "SIGMA-004", "title": "Scheduled Task Created by Non-Admin", "level": "medium", "rule": "selection:\n  EventID: 4698\n  User: '!NT AUTHORITY\\*'", "mitre": "T1053.005"},
    {"id": "SIGMA-005", "title": "DNS Query for Known Malicious Domain", "level": "critical", "rule": "selection:\n  EventID: 22\n  QueryName: '*evil*' OR '*c2*' OR '*beacon*'", "mitre": "T1071.004"},
    {"id": "SIGMA-006", "title": "Process Created from Suspicious Location", "level": "high", "rule": "selection:\n  EventID: 4688\n  NewProcessName: '*\\Temp\\*' OR '*\\Users\\Public\\*'", "mitre": "T1204.002"},
]

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "list_rules":
        return SIGMA_RULES
    elif action == "get_rule":
        rule_id = params.get("rule_id", "SIGMA-001")
        matches = [r for r in SIGMA_RULES if r["id"] == rule_id]
        return matches if matches else [{"error": f"Rule {rule_id} not found"}]
    elif action == "match_logs":
        event_id = params.get("event_id", 4663)
        matched = [r for r in SIGMA_RULES if any(str(event_id) in r["rule"])]
        return matched if matched else [{"info": "No rules matched for this event"}]
    elif action == "search_by_mitre":
        mitre_id = params.get("mitre_id", "T1003.001")
        matched = [r for r in SIGMA_RULES if mitre_id in r["mitre"]]
        return matched if matched else [{"info": f"No rules for {mitre_id}"}]
    else:
        return [{"error": f"Unknown action: {action}"}]
