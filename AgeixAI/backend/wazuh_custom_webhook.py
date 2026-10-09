#!/usr/bin/env python3
"""
AgeixAISOC — Wazuh Custom Integration Webhook.

Place this script at /var/ossec/integrations/custom-ageixai.py on the Wazuh VM
(192.168.56.30) and configure ossec.conf to trigger it on alerts with
level >= 7.

The script reads a JSON alert from stdin (Wazuh integration protocol),
filters by severity, and POSTs a structured payload to the AgeixAI
backend running at http://192.168.56.1:8000/webhook/wazuh-alert.

=========================================================================
INSTALLATION INSTRUCTIONS (run on Wazuh VM as root):
=========================================================================

  1. Copy this file to Wazuh:
     scp wazuh_custom_webhook.py root@192.168.56.30:/var/ossec/integrations/custom-ageixai.py
     ssh root@192.168.56.30 "chmod 750 /var/ossec/integrations/custom-ageixai.py && chown root:ossec /var/ossec/integrations/custom-ageixai.py"

  2. Add to /var/ossec/etc/ossec.conf (inside <ossec_config> block):

     <integration>
       <name>custom-ageixai</name>
       <hook_url>http://192.168.56.1:8000/webhook/wazuh-alert</hook_url>
       <level>7</level>
       <group>authentication,syslog,ids</group>
       <alert_format>json</alert_format>
     </integration>

  3. Restart Wazuh manager:
     systemctl restart wazuh-manager

  4. Verify:
     tail -f /var/ossec/logs/integrations.log
     # Look for: "custom-ageixai: forwarded alert to http://192.168.56.1:8000/webhook/wazuh-alert"

=========================================================================
Wazuh Integration Protocol:
  - Wazuh calls the script with:  <hook_url>  <alert_json_stdin>
  - The script receives the alert as JSON on stdin (first argument is the URL)
  - Output is logged to /var/ossec/logs/integrations.log
=========================================================================
"""

import json
import os
import sys
import urllib.request
import urllib.error
import logging
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration — override via environment or keep defaults
# ---------------------------------------------------------------------------

DEFAULT_HOOK_URL = "http://192.168.56.1:8000/webhook/wazuh-alert"
MIN_ALERT_LEVEL = int(os.environ.get("WAZUH_INTEGRATION_LEVEL", "7"))
TIMEOUT_SECONDS = 10

# Wazuh integration log
logging.basicConfig(
    filename="/var/ossec/logs/integrations.log",
    level=logging.INFO,
    format="%(asctime)s  custom-ageixai:  %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
)
logger = logging.getLogger("custom-ageixai")


def extract_fields(alert: dict) -> dict:
    """Extract and normalize fields from a Wazuh alert into AgeixAI schema."""
    rule = alert.get("rule", {}) or {}
    data = alert.get("data", {}) or {}
    agent = alert.get("agent", {}) or {}
    location = alert.get("location", "")

    # ── Rule info ───────────────────────────────────────────────────────
    rule_id = rule.get("id", 0) or rule.get("rule_id", 0)
    try:
        rule_id = int(rule_id)
    except (ValueError, TypeError):
        rule_id = 0

    rule_description = rule.get("description") or rule.get("mail", {}).get("subject", "") or ""

    # ── Level ───────────────────────────────────────────────────────────
    level = int(rule.get("level", 0) or 0)
    if level >= 12:
        severity = "critical"
    elif level >= 9:
        severity = "high"
    elif level >= 7:
        severity = "medium"
    else:
        severity = "low"

    # ── IP addresses ────────────────────────────────────────────────────
    src_ip = (
        data.get("src_ip")
        or data.get("srcip")
        or data.get("src_ip_address")
        or alert.get("src_ip", "")
        or ""
    )
    dst_ip = (
        data.get("dst_ip")
        or data.get("dstip")
        or data.get("dst_ip_address")
        or alert.get("dst_ip", "")
        or ""
    )

    # ── Agent hostname ──────────────────────────────────────────────────
    agent_name = agent.get("name", "unknown")

    # ── Full event ──────────────────────────────────────────────────────
    full_log = alert.get("full_log", "")

    return {
        "rule_id": rule_id,
        "rule_description": rule_description[:500],
        "src_ip": str(src_ip),
        "dst_ip": str(dst_ip),
        "severity": severity,
        "agent_name": str(agent_name),
        "raw_event": {
            "rule": rule,
            "data": data,
            "agent": agent,
            "location": location,
            "full_log": full_log[:2000],
            "timestamp": alert.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "decoder": alert.get("decoder", {}),
            "id": alert.get("id", ""),
        },
    }


def main() -> int:
    # ── Parse arguments ─────────────────────────────────────────────────
    # Wazuh integration protocol: argv[1] = hook_url, stdin = alert JSON
    hook_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOOK_URL

    try:
        raw_alert = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, KeyboardInterrupt) as exc:
        logger.error("Failed to parse alert JSON from stdin: %s", exc)
        return 1

    # ── Filter by level ─────────────────────────────────────────────────
    rule = raw_alert.get("rule", {}) or {}
    level = int(rule.get("level", 0) or 0)
    if level < MIN_ALERT_LEVEL:
        # Alert below threshold — silently drop
        return 0

    # ── Build payload ───────────────────────────────────────────────────
    payload = extract_fields(raw_alert)
    alert_summary = f"rule_id={payload['rule_id']} level={level} src={payload['src_ip']} dst={payload['dst_ip']} agent={payload['agent_name']}"
    logger.info("Forwarding alert: %s", alert_summary)

    # ── POST to AgeixAI backend ─────────────────────────────────────────
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        hook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Wazuh-AgeixAI-Integration/2.0",
        },
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)
        response_body = resp.read().decode("utf-8", errors="replace")
        logger.info("Backend responded HTTP %d: %s", resp.status, response_body[:200])
        return 0
    except urllib.error.HTTPError as exc:
        logger.error("Backend returned HTTP %d: %s", exc.code, exc.read().decode("utf-8", errors="replace")[:200])
        return 1
    except urllib.error.URLError as exc:
        logger.error("Backend unreachable at %s: %s", hook_url, exc.reason)
        return 1
    except Exception as exc:
        logger.error("Unexpected error posting to backend: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
