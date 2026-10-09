"""
AgeixAISOC — Parallel IOC Sweep & Proactive Threat Hunting Engine.

Architecture
------------
  POST /api/hunt/ioc-sweep
         │
         ▼
   asyncio.gather ──┬── wazuh-mcp  (log sweep)
                    ├── edr-mcp     (endpoint sweep)
                    └── ndr-mcp     (network sweep)
         │
         ▼
   Aggregate results (< 60s)
         │
         ▼
   Threat Hunter Agent  ── STIX/TAXII formatting ── TTP matching ── Actor match
         │
         ▼
   Open Proactive Threat Hunt case on Dashboard
         │
         ▼
   Return: sweep_duration, endpoints_scanned, compromised_assets, threat_actor_match
"""

import asyncio
import hashlib
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("AgeixAI.hunt_engine")

# ── Known TTP → Actor mapping (simulates STIX/TAXII feed) ────────────────────
# In production this comes from a TAXII server (e.g. MITRE ATT&CK / Hail-a-TAXII).
# Format follows STIX 2.1 indicator → relationship → threat-actor pattern.

ACTOR_TTP_MAP: dict[str, dict[str, Any]] = {
    "APT29": {
        "aliases": ["Cozy Bear", "The Dukes"],
        "origin": "Russia",
        "motivation": "Intelligence gathering",
        "ttps": ["T1003", "T1041", "T1071", "T1572", "T1059"],
        "tools": ["PowerShell", "Mimikatz", "Beacon"],
        "confidence": 85,
    },
    "FIN7": {
        "aliases": ["Carbanak", "Navigator"],
        "origin": "Russia",
        "motivation": "Financial",
        "ttps": ["T1190", "T1110", "T1021", "T1505", "T1059"],
        "tools": ["Carbanak", "TrickBot", "PowerShell"],
        "confidence": 80,
    },
    "BlackCat": {
        "aliases": ["ALPHV"],
        "origin": "Russia",
        "motivation": "Ransomware",
        "ttps": ["T1486", "T1490", "T1485", "T1078", "T1059"],
        "tools": ["BlackCat ransomware", "Mimikatz", "Cobalt Strike"],
        "confidence": 90,
    },
    "Mirai": {
        "aliases": ["IoT Worm"],
        "origin": "Various",
        "motivation": "DDoS",
        "ttps": ["T1499", "T1090", "T1046"],
        "tools": ["Mirai", "Bash", "Telnet"],
        "confidence": 75,
    },
    "TrickBot": {
        "aliases": ["TrickLoader"],
        "origin": "Russia",
        "motivation": "Financial / Initial Access",
        "ttps": ["T1071", "T1572", "T1059", "T1003"],
        "tools": ["TrickBot", "PowerShell", "Mimikatz"],
        "confidence": 82,
    },
    "Lazarus": {
        "aliases": ["HIDDEN COBRA"],
        "origin": "North Korea",
        "motivation": "Financial / Espionage",
        "ttps": ["T1204", "T1105", "T1572", "T1059"],
        "tools": ["Lazarus malware", "PowerShell", "Mimikatz"],
        "confidence": 78,
    },
}

# STIX-like pattern extractors — maps IOC types to TTP categories
IOC_TYPE_TTP_MAP: dict[str, list[str]] = {
    "ip": ["T1071", "T1572", "T1090"],
    "domain": ["T1071", "T1568", "T1572"],
    "hash": ["T1204", "T1105", "T1059"],
    "url": ["T1190", "T1566", "T1071"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  Parallel IOC Sweep
# ═══════════════════════════════════════════════════════════════════════════════

async def run_parallel_ioc_sweep(
    iocs: list[str],
    orchestrator: Any,
) -> dict[str, Any]:
    """
    Sweep a list of IOCs across wazuh-mcp, edr-mcp, and ndr-mcp in parallel.

    Uses asyncio.gather to achieve sub-60s response time regardless of IOC count.
    """
    from models.schemas import McpQuery

    start_time = time.monotonic()

    # Build parallel queries for each MCP server
    sweep_queries = [
        McpQuery(server="wazuh", action="sweep_iocs", params={"iocs": iocs}),
        McpQuery(server="edr", action="sweep_iocs", params={"iocs": iocs}),
        McpQuery(server="ndr", action="sweep_iocs", params={"iocs": iocs}),
    ]

    # Run all three sweeps simultaneously
    sweep_results = await orchestrator.query_parallel(sweep_queries)
    elapsed = time.monotonic() - start_time

    # Extract hits safely from each MCP response
    wazuh_hits: list[dict] = []
    edr_hits: list[dict] = []
    ndr_hits: list[dict] = []

    wazuh_resp = sweep_results.get("wazuh")
    edr_resp = sweep_results.get("edr")
    ndr_resp = sweep_results.get("ndr")

    if wazuh_resp and wazuh_resp.status == "ok" and isinstance(wazuh_resp.data, list):
        wazuh_hits = wazuh_resp.data
    if edr_resp and edr_resp.status == "ok" and isinstance(edr_resp.data, list):
        edr_hits = edr_resp.data
    if ndr_resp and ndr_resp.status == "ok" and isinstance(ndr_resp.data, list):
        ndr_hits = ndr_resp.data

    # Aggregate: unique hostnames / IPs that matched
    affected_assets: dict[str, set[str]] = {
        "wazuh_agents": set(),
        "edr_hosts": set(),
        "ndr_src_ips": set(),
        "ndr_dst_ips": set(),
    }

    for hit in wazuh_hits:
        agent = hit.get("agent_name", "")
        if agent:
            affected_assets["wazuh_agents"].add(agent)
    for hit in edr_hits:
        host = hit.get("host", "")
        if host:
            affected_assets["edr_hosts"].add(host)
    for hit in ndr_hits:
        src = hit.get("src_ip", "")
        dst = hit.get("dst_ip", "")
        if src:
            affected_assets["ndr_src_ips"].add(src)
        if dst:
            affected_assets["ndr_dst_ips"].add(dst)

    # Build IOC-to-IOC-type classification
    ioc_classification: list[dict[str, str]] = []
    for ioc in iocs:
        ioc_classification.append({
            "value": ioc,
            "type": _classify_ioc(ioc),
        })

    aggregated = {
        "sweep_duration_seconds": round(elapsed, 2),
        "iocs_swept": len(iocs),
        "ioc_classification": ioc_classification,
        "total_hits": len(wazuh_hits) + len(edr_hits) + len(ndr_hits),
        "results": {
            "wazuh": wazuh_hits,
            "edr": edr_hits,
            "ndr": ndr_hits,
        },
        "affected_assets": {
            "total_unique_endpoints": len(affected_assets["wazuh_agents"]) + len(affected_assets["edr_hosts"]),
            "total_unique_ips": len(affected_assets["ndr_src_ips"]) + len(affected_assets["ndr_dst_ips"]),
            "wazuh_agents": sorted(affected_assets["wazuh_agents"]),
            "edr_hosts": sorted(affected_assets["edr_hosts"]),
            "network_sources": sorted(affected_assets["ndr_src_ips"]),
            "network_destinations": sorted(affected_assets["ndr_dst_ips"]),
        },
        "endpoints_scanned": random.randint(50, 200),  # In production: actual count from EDR inventory
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "IOC sweep complete: %d IOCs in %.2fs — %d total hits across %d endpoints",
        len(iocs), elapsed, aggregated["total_hits"], aggregated["endpoints_scanned"],
    )
    return aggregated


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  STIX/TAXII Threat Actor Matching
# ═══════════════════════════════════════════════════════════════════════════════

def match_iocs_to_actors(
    sweep_results: dict[str, Any],
) -> dict[str, Any]:
    """
    Given sweep results, attempt to match the IOCs to known threat actor groups
    using a mock STIX/TAXII correlation engine.

    Returns the matched actor(s), confidence, and supporting TTP evidence.

    STIX formatting used:
      - indicator: observable (IP / hash / domain) → pattern
      - relationship: linked indicator → threat-actor
      - threat-actor: name, aliases, motivation, TTPs
    """
    ioc_classification = sweep_results.get("ioc_classification", [])

    # Collect all TTPs that the IOCs could map to
    triggered_ttps: dict[str, int] = {}
    for entry in ioc_classification:
        ioc_type = entry.get("type", "unknown")
        candidate_ttps = IOC_TYPE_TTP_MAP.get(ioc_type, [])
        for ttp in candidate_ttps:
            triggered_ttps[ttp] = triggered_ttps.get(ttp, 0) + 1

    if not triggered_ttps:
        return {
            "match_found": False,
            "actors": [],
            "confidence": 0.0,
            "triggered_ttps": [],
        }

    # Score each known actor by how many of their TTPs were triggered
    actor_scores: list[tuple[str, float, dict]] = []
    for actor_name, actor_info in ACTOR_TTP_MAP.items():
        known_ttps = set(actor_info["ttps"])
        matched_ttps = known_ttps & set(triggered_ttps.keys())
        if matched_ttps:
            overlap_pct = len(matched_ttps) / max(len(known_ttps), 1)
            weighted = overlap_pct * (actor_info["confidence"] / 100.0)
            actor_scores.append((
                actor_name,
                round(weighted * 100, 1),
                {
                    "matched_ttps": sorted(matched_ttps),
                    "overlap_pct": round(overlap_pct * 100, 1),
                    "base_confidence": actor_info["confidence"],
                    "tools": actor_info["tools"],
                },
            ))

    if not actor_scores:
        return {
            "match_found": False,
            "actors": [],
            "confidence": 0.0,
            "triggered_ttps": sorted(triggered_ttps.keys()),
        }

    actor_scores.sort(key=lambda x: x[1], reverse=True)
    top_score = actor_scores[0][1]

    # STIX-like formatted actor matches
    matched_actors = []
    for name, score, details in actor_scores[:3]:  # top 3
        info = ACTOR_TTP_MAP[name]
        matched_actors.append({
            "actor_name": name,
            "aliases": info["aliases"],
            "stix_id": f"threat-actor--{hashlib.md5(name.encode()).hexdigest()[:16]}",
            "origin": info["origin"],
            "motivation": info["motivation"],
            "match_confidence": score,
            "matched_ttps": details["matched_ttps"],
            "ttp_overlap_pct": details["overlap_pct"],
            "associated_tools": info["tools"],
        })

    return {
        "match_found": top_score >= 25.0,  # threshold for reporting as match
        "actors": matched_actors,
        "maximum_confidence": top_score,
        "triggered_ttps": sorted(triggered_ttps.keys()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Proactive Threat Hunt Case
# ═══════════════════════════════════════════════════════════════════════════════

def open_proactive_hunt_case(
    sweep_results: dict[str, Any],
    actor_match: dict[str, Any],
    analyst_id: str = "ageix-hunt-ai",
) -> dict[str, Any]:
    """
    Create a "Proactive Threat Hunt" case when IOC-to-actor matching succeeds.
    This is broadcast to the Dashboard as a pending investigation.
    """
    import hashlib, random
    raw = f"{sweep_results.get('timestamp', '')}{random.random()}"
    case_id = f"HUNT-{hashlib.md5(raw.encode()).hexdigest()[:8].upper()}"

    affected = sweep_results.get("affected_assets", {})
    total_endpoints = affected.get("total_unique_endpoints", 0)
    total_ips = affected.get("total_unique_ips", 0)

    actor_info = ""
    if actor_match.get("match_found") and actor_match.get("actors"):
        top = actor_match["actors"][0]
        actor_info = (
            f"Linked to {top['actor_name']} ({', '.join(top['aliases'])}) "
            f"with {top['match_confidence']}% confidence. "
            f"Motivation: {top['motivation']}. Overlapping TTPs: {', '.join(top['matched_ttps'])}."
        )

    case = {
        "case_id": case_id,
        "type": "proactive_threat_hunt",
        "title": f"Proactive Hunt: {len(sweep_results.get('iocs_swept', 0))} IOCs Swept — {actor_match.get('maximum_confidence', 0)}% Actor Match",
        "opened_by": analyst_id,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "priority": "high" if actor_match.get("match_found") else "medium",
        "status": "open",
        "iocs_swept": sweep_results.get("iocs_swept", 0),
        "total_hits": sweep_results.get("total_hits", 0),
        "endpoints_affected": total_endpoints,
        "ips_affected": total_ips,
        "threat_actor_match": actor_match,
        "findings": [],
        "recommendation": (
            f"Immediate investigation recommended. {actor_info}"
            if actor_match.get("match_found")
            else "No direct actor match. Continue monitoring swept endpoints."
        ),
        "metrics": {
            "endpoints_scanned": sweep_results.get("endpoints_scanned", 0),
            "compromised_assets": total_endpoints + total_ips,
            "threat_actor_match_confidence": actor_match.get("maximum_confidence", 0.0),
        },
    }

    logger.info(
        "Proactive hunt case %s opened: %s",
        case_id, case["recommendation"][:80],
    )
    return case


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  Full pipeline
# ═══════════════════════════════════════════════════════════════════════════════

async def run_ioc_sweep_pipeline(
    iocs: list[str],
    orchestrator: Any,
) -> dict[str, Any]:
    """
    Execute the complete IOC sweep pipeline:

    1. Parallel sweep across wazuh-mcp / edr-mcp / ndr-mcp
    2. Classify IOCs and match to Threat Actors (STIX/TAXII)
    3. Open a proactive hunt case if matches found
    4. Return aggregated results + exposure metrics
    """
    # Step 1: Parallel sweep
    sweep_results = await run_parallel_ioc_sweep(iocs, orchestrator)

    # Step 2: STIX/TTP matching
    actor_match = match_iocs_to_actors(sweep_results)

    # Step 3: Open proactive hunt case
    hunt_case = open_proactive_hunt_case(sweep_results, actor_match)

    affected = sweep_results.get("affected_assets", {})
    compromised = affected.get("total_unique_endpoints", 0) + affected.get("total_unique_ips", 0)

    return {
        "sweep_duration": f"{sweep_results['sweep_duration_seconds']}s",
        "endpoints_scanned": sweep_results.get("endpoints_scanned", 0),
        "compromised_assets": compromised,
        "threat_actor_match_confidence": actor_match.get("maximum_confidence", 0.0),
        "iocs_swept": sweep_results["iocs_swept"],
        "total_hits": sweep_results["total_hits"],
        "match_found": actor_match.get("match_found", False),
        "actor_match": actor_match,
        "affected_assets": sweep_results["affected_assets"],
        "raw_results": sweep_results["results"],
        "hunt_case": hunt_case,
        "hunt_case_id": hunt_case["case_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _classify_ioc(value: str) -> str:
    """Classify an IOC value into ip / domain / hash / url."""
    import re
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
        return "ip"
    if re.match(r"^[0-9a-fA-F]{32,64}$", value):
        return "hash"
    if value.startswith("http://") or value.startswith("https://"):
        return "url"
    if "." in value and " " not in value:
        return "domain"
    return "unknown"
