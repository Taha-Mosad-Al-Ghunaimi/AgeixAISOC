import random
from typing import Any


SERVER_NAME = "forti-mcp"

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "get_firewall_rules":
        return _mock_rules()
    elif action == "block_ip":
        ip = params.get("ip", "0.0.0.0")
        return [{"status": "blocked", "ip": ip, "rule_id": f"BLOCK-{random.randint(1000, 9999)}"}]
    elif action == "get_vpn_status":
        return _mock_vpn()
    elif action == "get_threat_logs":
        return _mock_threat_logs()
    else:
        return [{"error": f"Unknown action: {action}"}]


def _mock_rules() -> list[dict[str, Any]]:
    return [
        {"id": "1001", "name": "Allow HTTP/HTTPS", "from": "wan", "to": "dmz", "action": "accept", "status": "enabled"},
        {"id": "1002", "name": "Allow RDP to VLAN 20", "from": "vpn", "to": "vlan20", "action": "accept", "status": "enabled"},
        {"id": "1003", "name": "Block Known Malicious IPs", "from": "wan", "to": "any", "action": "deny", "status": "enabled"},
        {"id": "1004", "name": "Allow DNS Outbound", "from": "any", "to": "wan", "action": "accept", "status": "enabled"},
    ]


def _mock_vpn() -> list[dict[str, Any]]:
    return [
        {"tunnel": "ssl-vpn-01", "status": "up", "users": random.randint(10, 50), "bytes_in": random.randint(1, 100), "bytes_out": random.randint(1, 50)},
        {"tunnel": "ipsec-01", "status": "up", "users": 0, "bytes_in": random.randint(100, 500), "bytes_out": random.randint(50, 200)},
    ]


def _mock_threat_logs() -> list[dict[str, Any]]:
    return [
        {"type": "ips", "signature": "Log4j.RCE.Exploit", "src_ip": f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}", "dst_ip": "10.0.1.10", "action": "blocked"},
        {"type": "antivirus", "signature": "Malware.Generic.Beacon", "src_ip": "10.0.3.22", "dst_ip": "185.130.5.23", "action": "detected"},
        {"type": "web_filter", "signature": "Malicious.Category", "src_ip": "10.0.2.50", "url": "evil-download.com/payload.exe", "action": "blocked"},
    ]
