import random
from typing import Any


SERVER_NAME = "rag-mcp"

KNOWLEDGE_BASES = {
    "past_incidents": ["Ransomware attack on finance VLAN — 2025-03-15", "Log4j exploitation in DMZ — 2025-06-22", "Phishing campaign targeting C-suite — 2025-09-01"],
    "threat_intel": ["APT29 uses DNS tunneling (T1572) for exfiltration", "BlackCat ransomware uses intermittent encryption", "FIN7 targets financial sector via web applications"],
    "sigma_rules": ["Sigma rule for LSASS access (T1003.001)", "Sigma rule for encoded PowerShell (T1059.001)", "Sigma rule for suspicious RDP (T1021.001)"],
    "iso_27001": ["A.12.6.1 — Management of technical vulnerabilities", "A.16.1.5 — Response to information security incidents", "A.13.1.1 — Network controls"],
    "cve_kev": ["CVE-2025-44228 — Log4j RCE (KEV)", "CVE-2024-6387 — OpenSSH regreSSHion (KEV)", "CVE-2023-23397 — SMB EoP (KEV)"],
    "cmdb": ["web-01: Ubuntu 22.04, Apache 2.4.57, 10.0.10.10", "dc-01: Windows Server 2025, AD DS, 10.0.40.10", "ws-01: Windows 11, Finance Dept, 10.0.30.50"],
    "historical_logs": ["2026-06-15: 3 failed logins on dc-01 from 10.0.1.50", "2026-06-20: SMB enumeration detected on file-server-01", "2026-07-01: C2 beaconing from workstation-22"],
}

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "query":
        kb = params.get("knowledge_base", "past_incidents")
        query = params.get("query", "")
        top_k = params.get("top_k", 3)
        return _mock_retrieve(kb, query, top_k)
    elif action == "list_bases":
        return [{"name": k, "document_count": len(v)} for k, v in KNOWLEDGE_BASES.items()]
    else:
        return [{"error": f"Unknown action: {action}"}]


def _mock_retrieve(kb: str, query: str, top_k: int) -> list[dict[str, Any]]:
    docs = KNOWLEDGE_BASES.get(kb, ["Unknown knowledge base"])
    results = []
    for i, doc in enumerate(docs[:top_k]):
        results.append({
            "id": f"{kb}-{i}",
            "content": doc,
            "metadata": {"source": kb, "relevance": "mock"},
            "score": round(random.uniform(0.7, 0.99), 4),
        })
    return results
