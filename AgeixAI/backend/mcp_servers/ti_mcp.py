import random
from datetime import datetime, timezone
from typing import Any


SERVER_NAME = "ti-mcp"

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "lookup_ip":
        ip = params.get("ip", "0.0.0.0")
        return _mock_ip_lookup(ip)
    elif action == "lookup_hash":
        file_hash = params.get("hash", "")
        return _mock_hash_lookup(file_hash)
    elif action == "get_recent_iocs":
        return _mock_recent_iocs()
    elif action == "get_actor_intel":
        actor = params.get("actor", "APT29")
        return _mock_actor_intel(actor)
    else:
        return [{"error": f"Unknown action: {action}"}]


def _mock_ip_lookup(ip: str) -> list[dict[str, Any]]:
    return [{
        "ip": ip,
        "reputation": random.choice(["malicious", "suspicious", "unknown"]),
        "threat_score": random.randint(30, 100),
        "tags": random.sample(["c2", "phishing", "malware", "scanner", "botnet"], k=random.randint(1, 3)),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "source": random.choice(["AlienVault", "VirusTotal", "AbuseIPDB"]),
    }]


def _mock_hash_lookup(file_hash: str) -> list[dict[str, Any]]:
    return [{
        "hash": file_hash,
        "malicious": random.random() > 0.4,
        "detection_rate": f"{random.randint(10, 60)}/70",
        "type": random.choice(["exe", "dll", "ps1", "vbs"]),
        "signature": random.choice(["Trojan.CobaltStrike", "Ransomware.LockBit", "Backdoor.Agent"]),
    }]


def _mock_recent_iocs() -> list[dict[str, Any]]:
    iocs = []
    for i in range(10):
        iocs.append({
            "value": f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}" if random.random() > 0.5 else hashlib.md5(str(i).encode()).hexdigest(),
            "type": random.choice(["ip", "domain", "hash", "url"]),
            "threat": random.choice(["Emotet", "APT29", "BlackCat", "Mirai", "TrickBot"]),
            "confidence": random.choice(["high", "medium"]),
            "added": datetime.now(timezone.utc).isoformat(),
        })
    return iocs

import hashlib


def _mock_actor_intel(actor: str) -> list[dict[str, Any]]:
    actors = {
        "APT29": {"alias": "Cozy Bear", "origin": "Russia", "motivation": "Intelligence gathering", "ttps": ["T1572", "T1003", "T1041", "T1071"], "tools": ["Beacon", "PowerShell", "Mimikatz"]},
        "FIN7": {"alias": "Carbanak", "origin": "Russia", "motivation": "Financial", "ttps": ["T1190", "T1110", "T1021", "T1505"], "tools": ["Carbanak", "TrickBot", "PowerShell"]},
        "BlackCat": {"alias": "ALPHV", "origin": "Russia", "motivation": "Ransomware", "ttps": ["T1486", "T1490", "T1485", "T1078"], "tools": ["BlackCat ransomware", "Mimikatz", "Cobalt Strike"]},
    }
    return [actors.get(actor, {"info": f"No intel available for {actor}"})]
