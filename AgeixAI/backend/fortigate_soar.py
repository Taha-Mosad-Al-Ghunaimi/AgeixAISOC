"""
AgeixAISOC — Real FortiGate SOAR Execution.

Connects to the FortiGate VM at 192.168.56.2 via REST API to execute
real firewall actions:

  - block_ip_real(ip_to_block)     — Creates firewall address + adds to blocked group
  - isolate_host_real(host_id)     — Creates firewall address + adds to quarantine group

API reference:
  https://docs.fortinet.com/document/fortigate/7.4.0/administration-guide/746838/rest-api
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from config import settings

logger = logging.getLogger("ageix.fortigate_soar")

# ---------------------------------------------------------------------------
# FortiGate REST API session
# ---------------------------------------------------------------------------

FGT_BASE = f"https://{settings.lab_fortigate_ip}/api/v2/cmdb"
FGT_HEADERS = {
    "Authorization": f"Bearer {settings.fgt_api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
FGT_SSL_VERIFY = False


async def _fgt_get(path: str) -> dict[str, Any]:
    url = f"{FGT_BASE}{path}"
    try:
        async with httpx.AsyncClient(verify=FGT_SSL_VERIFY, timeout=10) as client:
            resp = await client.get(url, headers=FGT_HEADERS)
            resp.raise_for_status()
            return resp.json()
    except httpx.RequestError as exc:
        logger.warning("FortiGate GET failed: %s — %s", url, exc)
        return {"status": "error", "error": str(exc)}


async def _fgt_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{FGT_BASE}{path}"
    try:
        async with httpx.AsyncClient(verify=FGT_SSL_VERIFY, timeout=10) as client:
            resp = await client.post(url, headers=FGT_HEADERS, json=body)
            resp.raise_for_status()
            return resp.json()
    except httpx.RequestError as exc:
        logger.warning("FortiGate POST failed: %s — %s", url, exc)
        return {"status": "error", "error": str(exc)}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "FortiGate POST error: %s → %d %s",
            url, exc.response.status_code, exc.response.text[:300],
        )
        return {"status": "error", "http_status": exc.response.status_code, "detail": exc.response.text[:300]}


async def _fgt_put(path: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{FGT_BASE}{path}"
    try:
        async with httpx.AsyncClient(verify=FGT_SSL_VERIFY, timeout=10) as client:
            resp = await client.put(url, headers=FGT_HEADERS, json=body)
            resp.raise_for_status()
            return resp.json()
    except httpx.RequestError as exc:
        logger.warning("FortiGate PUT failed: %s — %s", url, exc)
        return {"status": "error", "error": str(exc)}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "FortiGate PUT error: %s → %d %s",
            url, exc.response.status_code, exc.response.text[:300],
        )
        return {"status": "error", "http_status": exc.response.status_code, "detail": exc.response.text[:300]}


# ---------------------------------------------------------------------------
# Public SOAR actions
# ---------------------------------------------------------------------------


async def block_ip_real(ip_to_block: str) -> dict[str, Any]:
    """Create a firewall address object for the IP and add it to the blocked group.

    Steps:
      1. POST /firewall/address/  — create address object (type ipmask)
      2. GET  /firewall/addrgrp/  — fetch the blocked group
      3. PUT  /firewall/addrgrp/  — update the blocked group with the new address
    """
    addr_name = f"ageix-block-{ip_to_block.replace('.', '-')}"

    # Step 1: Create firewall address object
    addr_body = {
        "name": addr_name,
        "type": "ipmask",
        "subnet": f"{ip_to_block} 255.255.255.255",
        "comment": f"Blocked by AgeixAI SOC on {datetime.now().isoformat()}",
    }
    addr_result = await _fgt_post("/firewall/address/", addr_body)
    if addr_result.get("status") == "error":
        logger.warning("Address may already exist: %s", addr_result.get("detail", ""))

    # Step 2: Get current blocked group members
    grp_name = settings.fgt_blocked_grp
    grp_result = await _fgt_get(f"/firewall/addrgrp/?filter=name={grp_name}")

    existing_members = []
    if grp_result.get("http_status") != 200 and "results" not in grp_result:
        logger.warning("Group '%s' not found — attempting to create it", grp_name)
        create_grp = await _fgt_post("/firewall/addrgrp/", {
            "name": grp_name,
            "member": [{"name": addr_name}],
            "comment": "AgeixAI SOC — Blocked IPs",
        })
        if create_grp.get("status") == "error":
            return {
                "status": "partial",
                "action": "block_ip",
                "ip": ip_to_block,
                "address_created": addr_name,
                "group_error": f"Could not create or update group '{grp_name}'",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "status": "executed",
            "action": "block_ip",
            "ip": ip_to_block,
            "address": addr_name,
            "group": grp_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    results = grp_result.get("results", [])
    if results:
        existing_members = results[0].get("member", [])

    # Step 3: Update group with new member
    member_names = [m["name"] for m in existing_members if isinstance(m, dict)]
    if addr_name not in member_names:
        member_names.append(addr_name)

    update_result = await _fgt_put(
        f"/firewall/addrgrp/{grp_name}",
        {"member": [{"name": n} for n in member_names]},
    )

    if update_result.get("status") == "error":
        return {
            "status": "partial",
            "action": "block_ip",
            "ip": ip_to_block,
            "address_created": addr_name,
            "group_update_error": update_result.get("detail", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    logger.info("FortiGate block_ip: ip=%s address=%s group=%s members=%d", ip_to_block, addr_name, grp_name, len(member_names))
    return {
        "status": "executed",
        "action": "block_ip",
        "ip": ip_to_block,
        "address": addr_name,
        "group": grp_name,
        "group_member_count": len(member_names),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def isolate_host_real(host_identifier: str) -> dict[str, Any]:
    """Isolate a host by creating a firewall address and adding it to quarantine group."""
    is_mac = ":" in host_identifier or "-" in host_identifier
    addr_name = f"ageix-quarantine-{host_identifier.replace('.', '-').replace(':', '-')}"

    if is_mac:
        addr_body = {
            "name": addr_name,
            "type": "mac",
            "macaddr": host_identifier,
            "comment": f"Quarantined by AgeixAI SOC on {datetime.now().isoformat()}",
        }
    else:
        addr_body = {
            "name": addr_name,
            "type": "ipmask",
            "subnet": f"{host_identifier} 255.255.255.255",
            "comment": f"Quarantined by AgeixAI SOC on {datetime.now().isoformat()}",
        }

    await _fgt_post("/firewall/address/", addr_body)

    grp_name = settings.fgt_quarantine_grp
    grp_result = await _fgt_get(f"/firewall/addrgrp/?filter=name={grp_name}")

    existing_members = []
    if grp_result.get("http_status") == 200:
        results = grp_result.get("results", [])
        if results:
            existing_members = results[0].get("member", [])

    member_names = [m["name"] for m in existing_members if isinstance(m, dict)]
    if addr_name not in member_names:
        member_names.append(addr_name)

    update_result = await _fgt_put(
        f"/firewall/addrgrp/{grp_name}",
        {"member": [{"name": n} for n in member_names]},
    )

    if update_result.get("status") == "error":
        create_result = await _fgt_post("/firewall/addrgrp/", {
            "name": grp_name,
            "member": [{"name": addr_name}],
            "comment": "AgeixAI SOC — Quarantined Hosts",
        })
        if create_result.get("status") == "error":
            return {
                "status": "partial",
                "action": "isolate_host",
                "host": host_identifier,
                "error": f"Could not create quarantine group '{grp_name}'",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    logger.info("FortiGate isolate_host: host=%s address=%s group=%s", host_identifier, addr_name, grp_name)
    return {
        "status": "executed",
        "action": "isolate_host",
        "host": host_identifier,
        "address": addr_name,
        "group": grp_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
