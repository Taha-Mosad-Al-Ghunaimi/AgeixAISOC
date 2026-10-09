from typing import Any, Literal

KnowledgeBaseName = Literal[
    "past_incidents", "threat_intel", "sigma_rules",
    "iso_27001", "cve_kev", "cmdb", "historical_logs",
    "learned_decisions", "external_threat_intel",
    "soc_academy",
]

KNOWLEDGE_BASE_METADATA: dict[KnowledgeBaseName, dict[str, Any]] = {
    "past_incidents": {
        "name": "Past Incidents",
        "description": "Historical security incident reports, post-mortems, and lessons learned",
        "document_count": 142,
        "embedding_model": "text-embedding-ada-002",
    },
    "threat_intel": {
        "name": "Threat Intelligence",
        "description": "Structured threat intel feeds including actor profiles, TTPs, and IOCs",
        "document_count": 3851,
        "embedding_model": "text-embedding-ada-002",
    },
    "sigma_rules": {
        "name": "Sigma Rules",
        "description": "Generic signature format for SIEM detection rules",
        "document_count": 892,
        "embedding_model": "text-embedding-ada-002",
    },
    "iso_27001": {
        "name": "ISO 27001 / NIST CSF",
        "description": "Controls, policies, and mappings from ISO 27001 and NIST Cybersecurity Framework",
        "document_count": 214,
        "embedding_model": "text-embedding-ada-002",
    },
    "cve_kev": {
        "name": "CVE / KEV Catalog",
        "description": "Known Exploited Vulnerabilities catalog from CISA and NVD",
        "document_count": 1203,
        "embedding_model": "text-embedding-ada-002",
    },
    "cmdb": {
        "name": "CMDB",
        "description": "Configuration Management Database — asset inventory, owners, patch status",
        "document_count": 573,
        "embedding_model": "text-embedding-ada-002",
    },
    "historical_logs": {
        "name": "Historical Logs",
        "description": "Ingested and indexed historical log data for proactive threat hunting",
        "document_count": 2850000,
        "embedding_model": "text-embedding-ada-002",
    },
    "learned_decisions": {
        "name": "Learned Decisions",
        "description": "Adaptive RAG memory — past human decisions on similar alerts. Grows with every HITL review.",
        "document_count": 0,
        "embedding_model": "text-embedding-ada-002",
    },
    "external_threat_intel": {
        "name": "External Threat Intelligence",
        "description": "OSINT & Dark Web intelligence reports — leaked credentials, ransomware mentions, and target profiling from the OSINT Swarm.",
        "document_count": 0,
        "embedding_model": "text-embedding-ada-002",
    },
    "soc_academy": {
        "name": "SOC Academy",
        "description": "Structured SOC Analyst Roadmap — 14 domains, sub-topics, and MITRE ATT&CK mappings for junior analyst training.",
        "document_count": 14,
        "embedding_model": "text-embedding-ada-002",
    },
}


def get_kb_names() -> list[str]:
    return list(KNOWLEDGE_BASE_METADATA.keys())


def get_kb_metadata(name: KnowledgeBaseName) -> dict[str, Any]:
    return KNOWLEDGE_BASE_METADATA.get(name, {"name": name, "description": "Unknown KB", "document_count": 0})
