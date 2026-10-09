"""
AgeixAISOC — Dynamic Deception Engine (n8n & FortiGate Integration).

Pipeline when HITL approves a "deceive_attacker" action:
  1. Send webhook to n8n (mock)  →  n8n triggers FortiGate API call
  2. FortiGate changes routing policy  →  attacker IP redirected to VLAN 30
  3. Cowrie Honeypot captures attacker commands  →  streamed to Dashboard

Architecture:
  HITL Approve "deceive_attacker"
         │
         ▼
   ┌──────────────────┐
   │  n8n Webhook     │  POST /webhook/n8n/deception (mock)
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │  FortiGate API   │  PATCH /api/v2/cmdb/router/policy  →  redirect to VLAN 30
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │  Cowrie Honeypot  │  Mock SSH session logs → live feed via WS + REST
   └──────────────────┘
"""

import asyncio
import hashlib
import json
import logging
import random
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("AgeixAI.deception")

# ── Mock Cowrie Honeypot command sequences ──────────────────────────────────
# These mimic real SSH sessions captured by Cowrie (medium-interaction honeypot).

COWRIE_SESSIONS: dict[str, list[dict[str, str]]] = {
    "default": [
        {"cmd": "whoami",                  "output": "postgres"},
        {"cmd": "hostname",                "output": "db-replica-02"},
        {"cmd": "cat /etc/hosts",          "output": "127.0.0.1 localhost\n10.0.30.10 db-primary\n10.0.30.20 app-server"},
        {"cmd": "ls -la /var/lib/postgresql/data/", "output": "total 48\ndrwx------ 7 postgres postgres 4096 .\n-rw------- 1 postgres postgres 45678 postgresql.conf"},
        {"cmd": "psql -l",                 "output": "List of databases\nName       | Owner\ncustomers  | postgres\nfinance    | postgres\nnorthwind  | postgres"},
        {"cmd": "cat /home/admin/.ssh/authorized_keys", "output": "ssh-rsa AAAA... attacker-key-here\nssh-rsa AAAA... backup-key"},
        {"cmd": "find / -name '*.sql' 2>/dev/null", "output": "/opt/backups/db_backup_2026-07-11.sql\n/home/admin/scripts/export_customers.sql"},
        {"cmd": "curl -s http://10.0.30.20/login -d 'user=admin&pass=admin123'", "output": "HTTP/1.1 302 Found\nLocation: /dashboard\nSet-Cookie: session=eyJhZG1pbiI6dHJ1ZX0="},
        {"cmd": "python3 -c \"import socket; s=socket.socket(); s.connect(('10.0.30.10',4444)); s.send(b'data'); s.close()\"", "output": ""},
        {"cmd": "sqlmap -u http://10.0.30.20/login --data='user=admin' --batch", "output": "[INFO] parameter 'user' is vulnerable\n[INFO] back-end DBMS: PostgreSQL\n[INFO] retrieving data: admin / admin123"},
    ],
    "lateral": [
        {"cmd": "whoami",                  "output": "root"},
        {"cmd": "hostname",                "output": "web-staging-01"},
        {"cmd": "ip addr show eth0",       "output": "inet 10.0.30.15/24 brd 10.0.30.255 scope global eth0"},
        {"cmd": "arp -a",                  "output": "10.0.30.1   ?   ether  00:50:56:aa:bb:cc\n10.0.30.10  ?   ether  00:50:56:dd:ee:ff"},
        {"cmd": "cat /etc/nginx/sites-enabled/default", "output": "server {\n    listen 443 ssl;\n    server_name intranet.corp.internal;\n    proxy_pass http://10.0.30.20:8080;\n}"},
        {"cmd": "nmap -sS -p 22,443,8080,3389 10.0.30.0/24", "output": "Nmap scan report for 10.0.30.1\nHost is up.\nPORT     STATE\n443/tcp  open\n\nNmap scan report for 10.0.30.10\nPORT     STATE\n22/tcp   open\n443/tcp  open\n8080/tcp open"},
        {"cmd": "ssh admin@10.0.30.10",    "output": "admin@10.0.30.10's password: \nLast login: Sun Jul 12 03:15:22 2026 from 10.0.30.15\nadmin@db-primary:~$"},
        {"cmd": "ps aux | grep postgres",  "output": "postgres  1234  0.5  2.1  ../../data/\npostgres  1235  0.2  1.8  ../../data/\npostgres  1240  0.0  0.5  postgres: writer"},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  n8n Webhook (mock)
# ═══════════════════════════════════════════════════════════════════════════════

N8N_WEBHOOK_URL = "https://n8n.corp.internal/webhook/ageixai/deception"

async def trigger_n8n_webhook(
    attacker_ip: str,
    session_id: str,
    action_id: str,
) -> dict[str, Any]:
    """
    Send a webhook to n8n to trigger the FortiGate routing change workflow.

    In production, this POSTs to the n8n webhook URL.
    n8n then calls the FortiGate API to update routing policies.
    Here we mock the entire flow.
    """
    payload = {
        "source": "ageixai-deception-engine",
        "event": "redirect_attacker",
        "attacker_ip": attacker_ip,
        "session_id": session_id,
        "action_id": action_id,
        "target_vlan": "VLAN-30-GHOST",
        "target_subnet": "10.0.30.0/24",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "n8n webhook sent to %s: redirect %s to VLAN 30 (session=%s)",
        N8N_WEBHOOK_URL, attacker_ip, session_id,
    )

    return {
        "webhook_url": N8N_WEBHOOK_URL,
        "status": "accepted",
        "payload": payload,
        "n8n_workflow_id": f"wf-deception-{hashlib.md5(action_id.encode()).hexdigest()[:8]}",
        "message": "n8n workflow triggered. FortiGate routing update in progress.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  FortiGate API Client (mock)
# ═══════════════════════════════════════════════════════════════════════════════

FORGITATE_API_URL = "https://fortigate.corp.internal/api/v2/cmdb/router/policy"

async def update_fortigate_routing(
    attacker_ip: str,
    session_id: str,
    target_vlan: str = "VLAN-30-GHOST",
) -> dict[str, Any]:
    """
    Mock the FortiGate API call to update routing policy.

    In production, this PATCHes FortiGate's CMDB API to:
      - Add a static route for the attacker IP to VLAN 30
      - Update the access policy to redirect HTTP/SSH/DB traffic to honeypots
      - Enable logging on the new policy for forensic capture
    """
    policy_id = random.randint(1000, 9999)

    logger.info(
        "FortiGate: policy %d updated — routing %s → %s",
        policy_id, attacker_ip, target_vlan,
    )

    return {
        "fortigate_url": FORGITATE_API_URL,
        "status": "success",
        "policy_id": policy_id,
        "policy_name": f"redirect-{attacker_ip.replace('.', '-')}",
        "action": "redirect_to_deception",
        "source_ip": attacker_ip,
        "destination_vlan": target_vlan,
        "destination_subnet": "10.0.30.0/24",
        "services_redirected": ["SSH (22)", "HTTP (80)", "HTTPS (443)", "PostgreSQL (5432)"],
        "logging_enabled": True,
        "packet_capture": True,
        "message": f"Attacker {attacker_ip} now routed to Ghost Deception Network (VLAN 30).",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Cowrie Honeypot Feed
# ═══════════════════════════════════════════════════════════════════════════════

async def get_cowrie_feed(
    session_id: str,
    scenario: str = "default",
) -> list[dict[str, str]]:
    """
    Return the full list of mock Cowrie commands for a given session.

    In production, this queries the Cowrie PostgreSQL/Elasticsearch database
    for the real commands the attacker executed inside the honeypot.
    """
    commands = COWRIE_SESSIONS.get(scenario, COWRIE_SESSIONS["default"])
    logger.info(
        "Cowrie feed: session=%s scenario=%s (%d commands)",
        session_id, scenario, len(commands),
    )
    return commands


async def stream_cowrie_commands(
    session_id: str,
    websocket: Any,
    delay: float = 2.5,
    scenario: str = "default",
) -> None:
    """
    Stream Cowrie honeypot commands to a WebSocket client in real time.

    Each command is sent after a realistic delay (simulating attacker think time).
    """
    commands = COWRIE_SESSIONS.get(scenario, COWRIE_SESSIONS["default"])
    for entry in commands:
        await asyncio.sleep(delay + random.uniform(0, 1.5))
        delay = max(1.0, delay * 0.9)
        try:
            payload = {
                "type": "cowrie_command",
                "session_id": session_id,
                "command": entry["cmd"],
                "output": entry["output"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await websocket.send_text(json.dumps(payload))
        except Exception:
            logger.warning("Cowrie stream: client disconnected (session=%s)", session_id)
            break

    try:
        await websocket.send_text(json.dumps({
            "type": "cowrie_complete",
            "session_id": session_id,
            "message": "[Cowrie session complete]",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  Full Deception Orchestration
# ═══════════════════════════════════════════════════════════════════════════════

async def execute_deception_pipeline(
    action_id: str,
    attacker_ip: str,
    decision_id: str,
    scenario: str = "default",
) -> dict[str, Any]:
    """
    Execute the complete Dynamic Deception pipeline when HITL approves
    a "deceive_attacker" action:

    1. Trigger n8n webhook
    2. FortiGate API — redirect attacker to VLAN 30
    3. Prepare Cowrie feed session
    4. Return session details for live streaming
    """
    session_id = f"cowrie-{hashlib.md5(f'{action_id}{datetime.now().isoformat()}'.encode()).hexdigest()[:8].upper()}"
    start_time = datetime.now(timezone.utc).isoformat()

    # Step 1: n8n webhook
    n8n_result = await trigger_n8n_webhook(attacker_ip, session_id, action_id)

    # Step 2: FortiGate routing update
    fortigate_result = await update_fortigate_routing(attacker_ip, session_id)

    logger.info(
        "Deception pipeline executed: %s → VLAN 30 (session=%s, n8n=%s, fortigate_policy=%s)",
        attacker_ip, session_id,
        n8n_result.get("n8n_workflow_id", "N/A"),
        fortigate_result.get("policy_id", "N/A"),
    )

    return {
        "status": "deception_active",
        "session_id": session_id,
        "attacker_ip": attacker_ip,
        "decision_id": decision_id,
        "action_id": action_id,
        "target_vlan": "VLAN-30-GHOST",
        "target_subnet": "10.0.30.0/24",
        "scenario": scenario,
        "started_at": start_time,
        "n8n": n8n_result,
        "fortigate": fortigate_result,
        "cowrie_commands": COWRIE_SESSIONS.get(scenario, COWRIE_SESSIONS["default"]),
        "message": f"Attacker {attacker_ip} redirected to Ghost Deception Network (VLAN 30). "
                   f"Cowrie honeypot session {session_id} active. Commands streaming via WebSocket.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  Smart Routing Logic
# ═══════════════════════════════════════════════════════════════════════════════

def get_smart_routing(risk_score: float) -> dict[str, Any]:
    """
    Determine the appropriate action based on risk score.

    Thresholds:
      > 90  → Auto-Block IP & Isolate Host
      70-89 → Redirect to Honeypot (Dynamic Deception)
      50-69 → Escalate to Analyst
      < 50  → Log & Monitor
    """
    if risk_score > 90:
        return {
            "action": "auto_block_and_isolate",
            "description": "Auto-Block IP & Isolate Host",
            "priority": "critical",
            "requires_hitl": True,
            "soar_action_type": "block_ip",
            "soar_action_type_secondary": "isolate_host",
            "playbook_refs": ["PB-001", "PB-003"],
        }
    elif risk_score >= 70:
        return {
            "action": "redirect_to_honeypot",
            "description": "Redirect to Honeypot (Dynamic Deception)",
            "priority": "high",
            "requires_hitl": True,
            "soar_action_type": "deceive_attacker",
            "playbook_refs": ["PB-009"],
        }
    elif risk_score >= 50:
        return {
            "action": "escalate_to_analyst",
            "description": "Escalate to Analyst",
            "priority": "medium",
            "requires_hitl": False,
            "soar_action_type": None,
            "playbook_refs": ["PB-010"],
        }
    else:
        return {
            "action": "log_and_monitor",
            "description": "Log & Monitor",
            "priority": "low",
            "requires_hitl": False,
            "soar_action_type": None,
            "playbook_refs": [],
        }
