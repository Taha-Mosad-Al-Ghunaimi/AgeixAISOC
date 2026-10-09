"""
SOC Academy & Knowledge Module.

Provides a structured SOC Analyst Roadmap embedded into RAG as the "soc_academy"
collection. Cross-references MITRE ATT&CK techniques to learning domains,
enabling the Recommendation Agent to suggest analyst training paths.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger("AgeixAI.soc_academy")

_ROADMAP: dict[str, Any] | None = None
_DOMAIN_BY_ID: dict[str, dict[str, Any]] = {}
_MITRE_TO_DOMAINS: dict[str, list[str]] = {}

ROADMAP_PATH = os.path.join(os.path.dirname(__file__), "soc_roadmap.json")


def _load_roadmap() -> dict[str, Any]:
    global _ROADMAP, _DOMAIN_BY_ID, _MITRE_TO_DOMAINS
    if _ROADMAP is not None:
        return _ROADMAP

    with open(ROADMAP_PATH, encoding="utf-8") as f:
        _ROADMAP = json.load(f)

    for domain in _ROADMAP.get("domains", []):
        did = domain["id"]
        _DOMAIN_BY_ID[did] = domain

    _MITRE_TO_DOMAINS = _ROADMAP.get("mitre_technique_domain_map", {})

    logger.info("SOC Academy loaded: %d domains, %d MITRE mappings",
                len(_DOMAIN_BY_ID), len(_MITRE_TO_DOMAINS))
    return _ROADMAP


def get_roadmap() -> dict[str, Any]:
    """Return the full structured roadmap JSON."""
    return _load_roadmap()


def get_domain(domain_id: str) -> dict[str, Any] | None:
    """Return a single domain by ID."""
    _load_roadmap()
    return _DOMAIN_BY_ID.get(domain_id)


def query_training_hint(mitre_techniques: list[str]) -> str:
    """
    Given a list of MITRE technique IDs (e.g. ["T1110", "T1003"]),
    return a formatted training hint string for a junior analyst.

    Example output:
        "This alert uses MITRE T1110, T1003. Review the 'Incident Detection',
         'Log Analysis', and 'Malware Analysis' modules in your SOC Academy."
    """
    _load_roadmap()
    if not mitre_techniques:
        return ""

    matched_domain_ids: set[str] = set()
    for technique in mitre_techniques:
        domains = _MITRE_TO_DOMAINS.get(technique, [])
        matched_domain_ids.update(domains)

    if not matched_domain_ids:
        return ""

    matched_domains = [_DOMAIN_BY_ID[did] for did in matched_domain_ids if did in _DOMAIN_BY_ID]
    if not matched_domains:
        return ""

    tech_list = ", ".join(mitre_techniques)
    domain_names = [d["name"] for d in matched_domains]
    if len(domain_names) == 1:
        return (
            f"This alert uses MITRE {tech_list}. "
            f"Review the '{domain_names[0]}' module in your SOC Academy."
        )
    domain_list = ", ".join(f"'{n}'" for n in domain_names[:-1])
    return (
        f"This alert uses MITRE {tech_list}. "
        f"Review the {domain_list} and '{domain_names[-1]}' modules in your SOC Academy."
    )


def seed_soc_academy(store: Any) -> int:
    """
    Embed each domain's content as a document in the soc_academy RAG collection.
    Call once on application startup.

    Returns the number of documents seeded.
    """
    _load_roadmap()
    roadmap = _ROADMAP
    if not roadmap:
        return 0

    seeded = 0
    for domain in roadmap.get("domains", []):
        did = domain["id"]
        name = domain["name"]
        description = domain["description"]
        topics = domain.get("topics", [])
        techniques = domain.get("mitre_techniques", [])

        content = (
            f"Domain: {name}\n"
            f"Description: {description}\n"
            f"MITRE Techniques: {', '.join(techniques) if techniques else 'N/A'}\n"
            f"Topics:\n" + "\n".join(f"  - {t}" for t in topics)
        )

        doc_id = f"soc-{did}"
        metadata = {
            "doc_id": doc_id,
            "domain_id": did,
            "domain_name": name,
            "mitre_techniques": techniques,
            "topic_count": len(topics),
            "type": "soc_academy_domain",
        }

        store.insert("soc_academy", doc_id, content, metadata)
        seeded += 1

    logger.info("SOC Academy seeded: %d domains into RAG collection 'soc_academy'", seeded)
    return seeded
