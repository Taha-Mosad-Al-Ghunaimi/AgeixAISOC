import random
from typing import Any


SERVER_NAME = "red-mcp"

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "nmap_scan":
        target = params.get("target", "10.0.1.0/24")
        return _mock_nmap(target)
    elif action == "cve_lookup":
        service = params.get("service", "apache")
        return _mock_cve(service)
    elif action == "metasploit_check":
        cve_id = params.get("cve_id", "CVE-2025-44228")
        return _mock_msf(cve_id)
    elif action == "exploit_simulate":
        target = params.get("target", "10.0.1.50")
        technique = params.get("technique", "eternalblue")
        return _mock_exploit(target, technique)
    else:
        return [{"error": f"Unknown action: {action}"}]


def _mock_nmap(target: str) -> list[dict[str, Any]]:
    hosts = []
    for i in range(random.randint(3, 6)):
        hosts.append({
            "ip": f"10.0.1.{random.randint(1, 50)}",
            "hostname": f"srv-{random.randint(1, 50):03d}",
            "state": "up",
            "ports": [
                {"port": 22, "service": "ssh", "state": "open", "version": "OpenSSH 8.9p1"},
                {"port": 80, "service": "http", "state": "open", "version": "Apache 2.4.57"},
                {"port": 445, "service": "smb", "state": "open", "version": "Samba 4.15.0"},
            ],
            "os": random.choice(["Windows Server 2022", "Ubuntu 22.04", "Debian 11"]),
        })
    return hosts


def _mock_cve(service: str) -> list[dict[str, Any]]:
    cve_db = {
        "apache": [{"cve_id": "CVE-2025-44228", "cvss": 9.8, "description": "Log4j RCE", "exploit_available": True}],
        "ssh": [{"cve_id": "CVE-2024-6387", "cvss": 8.1, "description": "OpenSSH regreSSHion", "exploit_available": True}],
        "smb": [{"cve_id": "CVE-2023-23397", "cvss": 9.1, "description": "SMB Elevation of Privilege", "exploit_available": True}],
    }
    return cve_db.get(service.lower(), [{"info": "No CVEs found for this service"}])


def _mock_msf(cve_id: str) -> list[dict[str, Any]]:
    return [{
        "cve_id": cve_id,
        "msf_module": f"exploit/multi/http/{cve_id.lower().replace('-', '_')}",
        "rank": "excellent",
        "targets": ["Automatic", "Linux x64", "Windows x64"],
    }]


def _mock_exploit(target: str, technique: str) -> list[dict[str, Any]]:
    return [{
        "target": target,
        "technique": technique,
        "result": random.choice(["COMPROMISED", "PATCHED - Not exploitable", "TIMEOUT"]),
        "access_level": random.choice(["user", "admin", "system"]) if random.random() > 0.3 else None,
    }]
