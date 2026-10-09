"""
AgeixAISOC — LangGraph Master Orchestrator.
6-node StateGraph with Short-Term Memory. Outputs a Decision Package JSON.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agents import (
    threat_detection_agent,
    risk_scoring_agent,
    recommendation_agent,
    threat_hunter_agent,
    red_team_agent,
    forensics_agent,
    run_agent_task,
)
from config import settings

logger = logging.getLogger("ageix.orchestrator")

# ---------------------------------------------------------------------------
# Shared State (Short-Term Memory)
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    """LangGraph shared state — STM lives here across nodes."""

    raw_alert: dict[str, Any]
    stm_log: list[str]
    threat_detection_output: str
    forensics_output: str
    threat_hunt_output: str
    risk_scoring_output: str
    recommendation_output: str
    red_team_output: str
    decision_package: Optional[dict[str, Any]]


def create_initial_state(raw_alert: dict) -> AgentState:
    return {
        "raw_alert": raw_alert,
        "stm_log": [f"[{datetime.now(timezone.utc).isoformat()}] Orchestrator started"],
        "threat_detection_output": "",
        "forensics_output": "",
        "threat_hunt_output": "",
        "risk_scoring_output": "",
        "recommendation_output": "",
        "red_team_output": "",
        "decision_package": None,
    }


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------


def node_threat_detection(state: AgentState) -> dict:
    alert_json = json.dumps(state["raw_alert"], indent=2)
    result = run_agent_task(
        threat_detection_agent,
        f"Classify this SIEM alert and map to MITRE ATT&CK:\n{alert_json}\n"
        "Output JSON with: threat_name, threat_category, mitre_technique_id, "
        "mitre_tactic, iocs (list of dicts with type and value), confidence (0-100).",
    )
    return {
        "threat_detection_output": result,
        "stm_log": state["stm_log"]
        + [f"[{datetime.now(timezone.utc).isoformat()}] Threat Detection complete"],
    }


def node_forensics(state: AgentState) -> dict:
    alert_json = json.dumps(state["raw_alert"], indent=2)
    result = run_agent_task(
        forensics_agent,
        f"Query past incident memory for similar threats:\n{alert_json}\n"
        "Output JSON with: similar_incidents (list), recurrence_pattern, "
        "past_recommendations, lessons_learned.",
    )
    return {
        "forensics_output": result,
        "stm_log": state["stm_log"]
        + [f"[{datetime.now(timezone.utc).isoformat()}] Forensics query complete"],
    }


def node_threat_hunt(state: AgentState) -> dict:
    alert_json = json.dumps(state["raw_alert"], indent=2)
    result = run_agent_task(
        threat_hunter_agent,
        f"Search for CVEs and IoCs related to:\n{alert_json}\n"
        "Use WebSearch tool. Output JSON with: cves (list), related_campaigns, "
        "ioc_enrichment, osint_notes.",
    )
    return {
        "threat_hunt_output": result,
        "stm_log": state["stm_log"]
        + [f"[{datetime.now(timezone.utc).isoformat()}] Threat Hunt complete"],
    }


def node_risk_scoring(state: AgentState) -> dict:
    result = run_agent_task(
        risk_scoring_agent,
        f"Assess business risk for this threat:\n{json.dumps(state['raw_alert'], indent=2)}\n"
        f"Forensics: {state['forensics_output']}\nThreat Intel: {state['threat_hunt_output']}\n"
        "Output JSON with: risk_score (0-100), impact_level, financial_impact_usd, "
        "likelihood, affected_assets, regulatory_impact.",
    )
    return {
        "risk_scoring_output": result,
        "stm_log": state["stm_log"]
        + [f"[{datetime.now(timezone.utc).isoformat()}] Risk Scoring complete"],
    }


def node_recommendation(state: AgentState) -> dict:
    result = run_agent_task(
        recommendation_agent,
        f"Create SOAR playbook for:\n{json.dumps(state['raw_alert'], indent=2)}\n"
        f"Risk: {state['risk_scoring_output']}\n"
        "Output JSON with: recommended_action (block_ip|isolate_host|quarantine_file|investigate|no_action), "
        "playbook_steps (list), fortigate_commands, estimated_containment_minutes.",
    )
    return {
        "recommendation_output": result,
        "stm_log": state["stm_log"]
        + [f"[{datetime.now(timezone.utc).isoformat()}] Recommendation complete"],
    }


def node_red_team(state: AgentState) -> dict:
    result = run_agent_task(
        red_team_agent,
        f"Simulate attack paths for scenario:\n{json.dumps(state['raw_alert'], indent=2)}\n"
        f"Recommendation: {state['recommendation_output']}\n"
        "Output JSON with: attack_paths (list), gaps_found (list), "
        "recommended_defenses (list), priority_level.",
    )
    return {
        "red_team_output": result,
        "stm_log": state["stm_log"]
        + [f"[{datetime.now(timezone.utc).isoformat()}] Red Team simulation complete"],
    }


def node_synthesize(state: AgentState) -> dict:
    """Master Brain — synthesizes all agent outputs into final Decision Package."""
    try:
        td = json.loads(state["threat_detection_output"] if isinstance(state["threat_detection_output"], str) else "{}")
    except json.JSONDecodeError:
        td = {}
    try:
        rs = json.loads(state["risk_scoring_output"] if isinstance(state["risk_scoring_output"], str) else "{}")
    except json.JSONDecodeError:
        rs = {}
    try:
        rec = json.loads(state["recommendation_output"] if isinstance(state["recommendation_output"], str) else "{}")
    except json.JSONDecodeError:
        rec = {}

    package = {
        "decision_id": f"DEC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "threat_name": td.get("threat_name", "Unknown"),
        "threat_category": td.get("threat_category", "Uncategorized"),
        "mitre_technique_id": td.get("mitre_technique_id", "T0000"),
        "mitre_tactic": td.get("mitre_tactic", "Unknown"),
        "risk_score": rs.get("risk_score", 50),
        "impact_level": rs.get("impact_level", "medium"),
        "financial_impact_usd": rs.get("financial_impact_usd", 0),
        "confidence": td.get("confidence", 50),
        "recommended_action": rec.get("recommended_action", "investigate"),
        "playbook_steps": rec.get("playbook_steps", []),
        "fortigate_commands": rec.get("fortigate_commands", []),
        "containment_estimate_minutes": rec.get("estimated_containment_minutes", 0),
        "iocs": td.get("iocs", []),
        "affected_assets": rs.get("affected_assets", []),
        "forensics_insights": state.get("forensics_output", ""),
        "threat_intel": state.get("threat_hunt_output", ""),
        "red_team_insights": state.get("red_team_output", ""),
        "stm": state["stm_log"],
    }

    return {
        "decision_package": package,
        "stm_log": state["stm_log"]
        + [f"[{datetime.now(timezone.utc).isoformat()}] Decision Package compiled"],
    }


# ---------------------------------------------------------------------------
# Edge routing
# ---------------------------------------------------------------------------


def should_run_red_team(state: AgentState) -> Literal["red_team", "synthesize"]:
    risk = 50
    try:
        rs = json.loads(state["risk_scoring_output"] if isinstance(state["risk_scoring_output"], str) else "{}")
        risk = rs.get("risk_score", 50)
    except (json.JSONDecodeError, KeyError):
        pass
    return "red_team" if risk >= 60 else "synthesize"


# ---------------------------------------------------------------------------
# Build Graph
# ---------------------------------------------------------------------------

def build_pipeline() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("threat_detection", node_threat_detection)
    graph.add_node("forensics", node_forensics)
    graph.add_node("threat_hunt", node_threat_hunt)
    graph.add_node("risk_scoring", node_risk_scoring)
    graph.add_node("recommendation", node_recommendation)
    graph.add_node("red_team", node_red_team)
    graph.add_node("synthesize", node_synthesize)

    graph.add_edge(START, "forensics")
    graph.add_edge("forensics", "threat_hunt")
    graph.add_edge("threat_hunt", "threat_detection")
    graph.add_edge("threat_detection", "risk_scoring")
    graph.add_edge("risk_scoring", "recommendation")
    graph.add_conditional_edges(
        "recommendation",
        should_run_red_team,
        {"red_team": "red_team", "synthesize": "synthesize"},
    )
    graph.add_edge("red_team", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def run_orchestrator_pipeline(raw_alert: dict) -> dict:
    """Run the LangGraph orchestrator and return the decision package."""
    app = build_pipeline()
    state = create_initial_state(raw_alert)
    final_state = await app.ainvoke(state)
    return final_state.get("decision_package", {})
