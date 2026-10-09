"""
AgeixAISOC — FastAPI Application.
Endpoints:
  POST /webhook/wazuh-alert        — Receive Wazuh alerts, trigger LangGraph orchestrator.
  POST /webhook/wazuh-raw          — Receive raw Wazuh JSON webhook.
  WS   /ws/dashboard               — Broadcast real-time agent logs and Decision Packages.
  POST /api/human-decision         — HITL approve/reject → FortiGate SOAR execution.
  POST /api/lab/launch-attack      — SSH into Kali VM and run real offensive action.
  GET  /api/lab/status             — Check reachability of all 6 lab VMs.
  POST /api/lab/check-network      — Full network connectivity test.
  GET  /api/health                 — Health check.
  POST /api/analyze/malware-triage — AI Malware Triage (3-agent pipeline).
  GET  /api/rag/stats              — RAG memory statistics.
  POST /api/cracs/correlate        — Cross-Agent Correlation (campaign detection).
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Literal, Optional

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from orchestrator import run_orchestrator_pipeline
from malware_triage_engine import run_malware_triage
from rag_memory import rag as rag_memory
from cracs_engine import correlate_alerts
from fortigate_soar import block_ip_real, isolate_host_real
from lab_bridge import LabBridge, SshHost
from ueba_engine import predict_anomaly
from adaptive_rag import learn_from_human
from forensics_engine import generate_forensics_timeline
from vuln_predictor import predict_exploit_likelihood
from gap_loop import run_gap_loop
from hunt_engine import run_ioc_sweep
from osint import OTXClient
from deception_engine import execute_deception_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ageix")

# ── Lab Bridge — register all 6 VM hosts ──────────────────────────────────────

lab = LabBridge({
    "kali": SshHost(
        hostname=settings.lab_kali_ip,
        port=settings.lab_kali_port,
        username=settings.lab_kali_user,
        password=settings.lab_kali_pass,
    ),
    "win10": SshHost(
        hostname=settings.lab_win10_ip,
        port=22,
        username="Administrator",
        password="Passw0rd!",
    ),
    "metasploitable": SshHost(
        hostname=settings.lab_metasploitable_ip,
        port=22,
        username=settings.lab_metasploitable_user,
        password=settings.lab_metasploitable_pass,
    ),
    "wazuh": SshHost(
        hostname=settings.lab_wazuh_ip,
        port=22,
        username="root",
        password="",
    ),
    "fortigate": SshHost(
        hostname=settings.lab_fortigate_ip,
        port=22,
        username="admin",
        password="",
    ),
    "ad": SshHost(
        hostname=settings.lab_ad_ip,
        port=22,
        username="Administrator",
        password="Passw0rd!",
    ),
})

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class WazuhAlert(BaseModel):
    rule_id: int = Field(..., description="Wazuh rule ID")
    rule_description: str = Field(default="", description="Rule description")
    src_ip: str = Field("", description="Source IP")
    dst_ip: str = Field("", description="Destination IP")
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    agent_name: str = Field("unknown", description="Wazuh agent hostname")
    raw_event: dict[str, Any] = Field(default_factory=dict)


class WazuhRawAlert(BaseModel):
    """Raw Wazuh webhook payload."""
    timestamp: str = ""
    rule: Optional[dict] = None
    agent: Optional[dict] = None
    data: Optional[dict] = None
    location: str = ""
    full_log: str = ""


class HumanDecision(BaseModel):
    decision_id: str
    action: Literal["approve", "reject", "modify"]
    analyst_id: str = "soc-analyst"
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LabAttackRequest(BaseModel):
    attack_type: str = Field(default="ping_win10", description="Attack to run on Kali")
    target: str = Field(default="")


class WsMessage(BaseModel):
    type: str
    data: dict[str, Any] = {}
    message: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MalwareTriageRequest(BaseModel):
    hash: str


class UserActivityLog(BaseModel):
    user_id: str
    hour: int = Field(..., ge=0, le=23)
    data_downloaded_mb: float = 0.0
    failed_logins: int = 0
    source_ip: str = ""


# ---------------------------------------------------------------------------
# WebSocket Manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, message: dict):
        stale = []
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)

    @property
    def count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("AgeixAISOC Backend starting — LIVE LAB MODE")
    logger.info("  Host:          http://%s:%d", settings.host, settings.port)
    logger.info("  Ollama:        %s", settings.ollama_base_url)
    logger.info("  Kali:          %s", settings.lab_kali_ip)
    logger.info("  Win10 Victim:  %s", settings.lab_win10_ip)
    logger.info("  Metasploitable: %s", settings.lab_metasploitable_ip)
    logger.info("  Wazuh:         %s", settings.lab_wazuh_ip)
    logger.info("  FortiGate:     %s", settings.lab_fortigate_ip)
    logger.info("  AD Server:     %s", settings.lab_ad_ip)
    logger.info("  n8n Webhook:   %s", settings.n8n_soar_webhook)
    logger.info("=" * 60)
    yield
    logger.info("AgeixAISOC Backend shutting down")


app = FastAPI(title="AgeixAISOC", version="2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.56.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "AgeixAISOC",
        "version": "2.0",
        "connections": manager.count,
    }


@app.post("/webhook/wazuh-alert")
async def wazuh_alert(alert: WazuhAlert):
    """Receive Wazuh alert → run LangGraph orchestrator → store in RAG."""
    logger.info("Wazuh alert: rule_id=%d src_ip=%s dst_ip=%s", alert.rule_id, alert.src_ip, alert.dst_ip)

    raw = alert.model_dump()
    await manager.broadcast({
        "type": "agent_log",
        "source": "siem",
        "level": alert.severity,
        "message": f"Alert rule {alert.rule_id}: {alert.rule_description} from {alert.src_ip}",
    })

    # ── Run AI pipeline ────────────────────────────────────────────────
    try:
        decision = await run_orchestrator_pipeline(raw)
    except Exception as exc:
        logger.error("Orchestrator failed: %s", exc)
        await manager.broadcast({
            "type": "system_log",
            "source": "orchestrator",
            "level": "error",
            "message": f"Pipeline failed: {exc}",
        })
        return {"status": "error", "detail": str(exc)}

    # ── Auto-correlate via CRACS ────────────────────────────────────────
    try:
        cracs_result = correlate_alerts([raw])
        if cracs_result.get("campaign_detected"):
            await manager.broadcast({
                "type": "system_log",
                "source": "cracs",
                "level": "critical",
                "message": f"CRACS: {cracs_result['campaigns'][0]['campaign_name']} detected",
            })
    except Exception as exc:
        logger.warning("CRACS correlation failed: %s", exc)

    # ── Broadcast decision package ──────────────────────────────────────
    await manager.broadcast({
        "type": "decision_package",
        "decision_id": decision.get("decision_id"),
        "threat_name": decision.get("threat_name", "Unknown"),
        "mitre_technique": decision.get("mitre_technique_id", "T0000"),
        "risk_score": decision.get("risk_score", 50),
        "confidence": decision.get("confidence", 50),
        "recommended_action": decision.get("recommended_action", "investigate"),
        "iocs": decision.get("iocs", []),
        "src_ip": alert.src_ip,
        "dst_ip": alert.dst_ip,
        "message": f"Decision: {decision.get('recommended_action', 'investigate')} for {decision.get('threat_name', 'Unknown')}",
    })

    rag_memory.store_incident(decision)

    return {"status": "success", "decision": decision}


@app.post("/webhook/wazuh-raw")
async def wazuh_raw_alert(payload: WazuhRawAlert):
    """Receive raw Wazuh JSON webhook, parse, and forward to pipeline."""
    logger.info("Raw Wazuh webhook: location=%s", payload.location)

    src_ip = ""
    dst_ip = ""
    rule_id = 0
    rule_desc = payload.full_log[:200] if payload.full_log else ""

    if payload.data and isinstance(payload.data, dict):
        src_ip = payload.data.get("src_ip", "") or payload.data.get("srcip", "")
        dst_ip = payload.data.get("dst_ip", "") or payload.data.get("dstip", "")
        if not src_ip:
            src_ip = payload.data.get("src_ip_address", "")

    if payload.rule:
        rule_id = payload.rule.get("id", 0) or payload.rule.get("rule_id", 0)
        rule_desc = payload.rule.get("description", rule_desc)

    alert = WazuhAlert(
        rule_id=int(rule_id) if rule_id else 0,
        rule_description=str(rule_desc),
        src_ip=str(src_ip),
        dst_ip=str(dst_ip),
        severity="high" if int(rule_id) > 500 else "medium",
        agent_name=payload.agent.get("name", "unknown") if payload.agent else "unknown",
        raw_event=payload.model_dump(),
    )

    return await wazuh_alert(alert)


@app.post("/api/analyze/malware-triage")
async def malware_triage(req: MalwareTriageRequest):
    """Analyze a file hash with the Malware Triage Engine."""
    file_hash = req.hash.strip()
    if not file_hash:
        raise HTTPException(status_code=422, detail="Field 'hash' is required")

    logger.info("Malware triage: hash=%s", file_hash[:16])
    try:
        result = run_malware_triage(file_hash)
        await manager.broadcast({
            "type": "agent_log",
            "source": "malware_triage",
            "level": "info",
            "message": f"Triage complete: {result.get('threat_name', 'Unknown')} "
                       f"(verdict={result.get('verdict', 'unknown')})",
        })
        return result
    except Exception as exc:
        logger.error("Malware triage failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/rag/stats")
async def rag_stats():
    """Return RAG memory statistics."""
    return rag_memory.get_statistics()


@app.post("/api/cracs/correlate")
async def cracs_correlate(payload: dict):
    """Correlate batched alerts for multi-vector campaign detection."""
    alerts = payload.get("alerts", [])
    if not alerts:
        raise HTTPException(status_code=422, detail="Field 'alerts' is required")

    logger.info("CRACS correlate: %d alerts", len(alerts))
    try:
        result = correlate_alerts(alerts)
        if result.get("campaign_detected"):
            await manager.broadcast({
                "type": "system_log",
                "source": "cracs",
                "level": "critical",
                "message": f"CRACS: {len(result['campaigns'])} campaign(s) detected",
            })
        return result
    except Exception as exc:
        logger.error("CRACS failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# UEBA, Forensics, Vulns, Gap Loop, Hunt, OSINT — orphan modules wired live
# ---------------------------------------------------------------------------


@app.post("/api/ueba/ingest")
async def ueba_ingest(log: UserActivityLog):
    """Ingest user activity log for UEBA anomaly detection."""
    result = predict_anomaly(log.model_dump())
    if result.get("anomaly"):
        await manager.broadcast({
            "type": "agent_log",
            "source": "ueba",
            "level": "critical",
            "message": f"UEBA anomaly: {result.get('reason')} (score={result.get('anomaly_score', 0):.2f})",
        })
    return result


@app.get("/api/forensics/timeline")
async def forensics_timeline(decision_id: str = ""):
    """Generate forensic timeline for a given decision."""
    return {"timeline": generate_forensics_timeline(decision_id)}


@app.get("/api/vulns/predicted")
async def vulns_predicted():
    """Return predicted exploit-likelihood rankings."""
    return predict_exploit_likelihood()


@app.post("/api/gap-loop/run")
async def gap_loop_run(target: str = "metasploitable"):
    """Run the detection-gap feedback loop against a target."""
    return await run_gap_loop(target, lab)


@app.post("/api/hunt/ioc-sweep")
async def hunt_ioc_sweep(ioc: str, ioc_type: str = "ip"):
    """Sweep IOC across Wazuh / EDR / NDR MCP servers."""
    result = await run_ioc_sweep(ioc, ioc_type)
    await manager.broadcast({
        "type": "agent_log",
        "source": "hunt_engine",
        "level": "info",
        "message": f"IOC sweep complete: {len(result.get('matches', []))} matches for {ioc}",
    })
    return result


@app.get("/api/osint/ip/{ip}")
async def osint_ip_lookup(ip: str):
    """Look up IP reputation via AlienVault OTX."""
    import os
    client = OTXClient(api_key=os.getenv("OTX_API_KEY", ""))
    return client.lookup_ip(ip)


@app.post("/api/deception/execute")
async def deception_execute(attacker_ip: str = "", decision_id: str = ""):
    """Execute Dynamic Deception pipeline — redirect attacker to honeypot VLAN 30."""
    import uuid
    action_id = f"deceive-{uuid.uuid4().hex[:8]}"
    result = await execute_deception_pipeline(
        action_id=action_id,
        attacker_ip=attacker_ip or "0.0.0.0",
        decision_id=decision_id or "manual",
    )
    await manager.broadcast({
        "type": "agent_log",
        "source": "deception_engine",
        "level": "info",
        "message": f"Deception active: {attacker_ip} → VLAN-30-GHOST (session={result.get('session_id', 'N/A')})",
    })
    return result


@app.post("/api/human-decision")
async def human_decision(decision: HumanDecision):
    """Receive HITL decision. On approve → execute FortiGate block_ip_real + n8n webhook."""
    logger.info("Human decision: %s action=%s analyst=%s", decision.decision_id, decision.action, decision.analyst_id)

    await manager.broadcast({
        "type": "human_decision",
        "decision_id": decision.decision_id,
        "action": decision.action,
        "message": f"Analyst {decision.action} decision {decision.decision_id}",
    })

    if decision.action == "approve":
        # ── Extract context from metadata ───────────────────────────────
        src_ip = decision.metadata.get("src_ip", "")
        recommended_action = decision.metadata.get("recommended_action", "investigate")

        # ── 1. Execute FortiGate SOAR action ──────────────────────────
        if recommended_action == "block_ip" and src_ip:
            try:
                fgt_result = await block_ip_real(src_ip)
                logger.info("FortiGate block_ip result: %s", json.dumps(fgt_result))
                await manager.broadcast({
                    "type": "system_log",
                    "source": "fortigate_soar",
                    "level": "info",
                    "message": f"FortiGate blocked IP {src_ip} (status={fgt_result.get('status', 'unknown')})",
                })
            except Exception as exc:
                logger.error("FortiGate block_ip_real failed: %s", exc)

        elif recommended_action == "isolate_host":
            host_id = decision.metadata.get("target_host", "") or decision.metadata.get("dst_ip", "")
            if host_id:
                try:
                    iso_result = await isolate_host_real(host_id)
                    logger.info("FortiGate isolate result: %s", json.dumps(iso_result))
                    await manager.broadcast({
                        "type": "system_log",
                        "source": "fortigate_soar",
                        "level": "info",
                        "message": f"FortiGate isolated host {host_id}",
                    })
                except Exception as exc:
                    logger.error("FortiGate isolate_host_real failed: %s", exc)

        # ── 2. Forward to n8n SOAR webhook (optional) ──────────────────
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    settings.n8n_soar_webhook,
                    json={
                        "decision_id": decision.decision_id,
                        "action": decision.action,
                        "analyst": decision.analyst_id,
                        "notes": decision.notes,
                        "metadata": decision.metadata,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                logger.info("n8n webhook: %d %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("n8n webhook failed: %s", exc)

    learn_from_human(
        decision_package={"decision_id": decision.decision_id},
        human_action=decision.action,
        analyst_notes=decision.notes,
    )

    return {"status": "success", "decision_id": decision.decision_id, "action": decision.action}


@app.post("/api/lab/launch-attack")
async def launch_attack(req: LabAttackRequest):
    """SSH into Kali (192.168.56.10) and execute a real offensive action."""
    attack_name = req.attack_type or "ping_win10"
    logger.info("Launching attack: %s", attack_name)

    try:
        result = await lab.run_attack_by_name(attack_name)
        await manager.broadcast({
            "type": "agent_log",
            "source": "red_team",
            "level": "info",
            "message": f"Attack '{attack_name}' executed — success={result.get('success')}",
        })
        return {"status": "success" if result.get("success") else "failed", "result": result}
    except Exception as exc:
        logger.error("Attack failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/lab/status")
async def lab_status():
    """ICMP reachability check for all 6 lab VMs."""
    import subprocess
    import platform

    param = "-n" if platform.system().lower() == "windows" else "-c"
    vms = {
        "kali": settings.lab_kali_ip,
        "win10": settings.lab_win10_ip,
        "metasploitable": settings.lab_metasploitable_ip,
        "wazuh": settings.lab_wazuh_ip,
        "fortigate": settings.lab_fortigate_ip,
        "ad": settings.lab_ad_ip,
    }

    results = {}
    for name, ip in vms.items():
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", param, "1", ip,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            code = await proc.wait()
            results[name] = {
                "ip": ip,
                "reachable": code == 0,
                "latency_ms": None,
            }
        except Exception as exc:
            results[name] = {"ip": ip, "reachable": False, "error": str(exc)}

    return results


@app.post("/api/lab/check-network")
async def check_network():
    """Full network connectivity test across all lab VMs."""
    import subprocess
    import platform

    param = "-n" if platform.system().lower() == "windows" else "-c"
    vms = {
        "kali": settings.lab_kali_ip,
        "win10": settings.lab_win10_ip,
        "metasploitable": settings.lab_metasploitable_ip,
        "wazuh": settings.lab_wazuh_ip,
        "fortigate": settings.lab_fortigate_ip,
        "ad": settings.lab_ad_ip,
    }

    results = {}
    for name, ip in vms.items():
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", param, "2", "-W", "3", ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            results[name] = {
                "ip": ip,
                "reachable": proc.returncode == 0,
            }
        except Exception as exc:
            results[name] = {"ip": ip, "reachable": False, "error": str(exc)}

    return {"network_status": results, "timestamp": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws/dashboard")
async def websocket_dashboard(ws: WebSocket):
    await manager.connect(ws)
    logger.info("WebSocket connected (total: %d)", manager.count)

    try:
        await manager.broadcast({
            "type": "system_log",
            "source": "server",
            "level": "info",
            "message": "Client connected to dashboard",
        })

        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                logger.debug("WS message: %s", msg.get("type", "unknown"))
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected (total: %d)", manager.count - 1)
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        manager.disconnect(ws)
        await manager.broadcast({
            "type": "system_log",
            "source": "server",
            "level": "info",
            "message": "Client disconnected from dashboard",
        })
