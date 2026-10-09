import random
from datetime import datetime, timezone
from typing import Any


SERVER_NAME = "forensics-mcp"

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "collect_artifacts":
        host = params.get("host", "unknown")
        return _mock_artifacts(host)
    elif action == "analyze_memory":
        dump_path = params.get("dump_path", "/tmp/memdump.raw")
        return _mock_memory_analysis(dump_path)
    elif action == "analyze_disk":
        image_path = params.get("image_path", "/tmp/disk.dd")
        return _mock_disk_analysis(image_path)
    elif action == "timeline":
        host = params.get("host", "unknown")
        return _mock_timeline(host)
    elif action == "extract_iocs":
        artifact_id = params.get("artifact_id", "ART-001")
        return _mock_ioc_extraction(artifact_id)
    else:
        return [{"error": f"Unknown action: {action}"}]


def _mock_artifacts(host: str) -> list[dict[str, Any]]:
    return [
        {"type": "evtx", "path": f"C:\\Windows\\System32\\winevt\\Logs\\Security.evtx", "size_mb": random.randint(10, 200)},
        {"type": "prefetch", "path": f"C:\\Windows\\Prefetch\\", "files": random.randint(20, 150)},
        {"type": "registry", "path": "C:\\Windows\\System32\\config\\SAM"},
        {"type": "memory", "path": "/tmp/memdump.raw", "size_mb": random.randint(1024, 8192)},
    ]


def _mock_memory_analysis(dump_path: str) -> list[dict[str, Any]]:
    return [
        {"plugin": "pslist", "suspicious_processes": [
            {"pid": 1234, "name": "powershell.exe", "parent": 456, "cmdline": "powershell -enc SQBFAFgAIAAoAE4AZQB3..."},
            {"pid": 5678, "name": "rundll32.exe", "parent": 444, "cmdline": "rundll32.exe javascript:\"\\..\\mshtml,RunHTMLApplication\""},
        ]},
        {"plugin": "netscan", "suspicious_connections": [
            {"local": "10.0.1.50:49152", "remote": "185.142.53.22:4444", "proto": "TCP"},
        ]},
        {"plugin": "malfind", "detections": [
            {"pid": 1234, "protection": "RWX", "hex": "4d5a90...", "note": "Executable code in PowerShell process"},
        ]},
    ]


def _mock_disk_analysis(image_path: str) -> list[dict[str, Any]]:
    return [
        {"type": "deleted_files", "count": random.randint(5, 50), "recoverable": True},
        {"type": "recent_files", "paths": [
            "C:\\Users\\Public\\beacon.exe",
            "C:\\Users\\admin\\Documents\\passwords.txt",
            "C:\\Temp\\mimikatz.log",
        ]},
        {"type": "timestomped", "files": [
            "C:\\Windows\\System32\\svchost.exe", "C:\\ProgramData\\update.dll",
        ]},
    ]


def _mock_timeline(host: str) -> list[dict[str, Any]]:
    base = datetime.now(timezone.utc)
    return [
        {"timestamp": base.isoformat(), "event": "Process created: powershell.exe", "pid": 1234, "user": "SYSTEM"},
        {"timestamp": base.isoformat(), "event": "Network connection: 185.142.53.22:4444", "pid": 1234},
        {"timestamp": base.isoformat(), "event": "File created: C:\\Users\\Public\\beacon.exe", "pid": 1234},
        {"timestamp": base.isoformat(), "event": "Registry modification: Run key", "pid": 5678},
    ]


def _mock_ioc_extraction(artifact_id: str) -> list[dict[str, Any]]:
    return [
        {"type": "ip", "value": "185.142.53.22", "confidence": "high"},
        {"type": "domain", "value": "evil-c2.example.com", "confidence": "high"},
        {"type": "hash", "value": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6", "confidence": "medium"},
    ]
