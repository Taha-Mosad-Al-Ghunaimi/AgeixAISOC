"""
AgeixAISOC — 6 CrewAI Agents + Ollama LLM Setup.
"""

import logging
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Optional

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool

from llm_config import get_master_brain_llm, get_coder_llm, get_fast_triage_llm, get_osint_llm

logger = logging.getLogger("ageix.agents")

# ---------------------------------------------------------------------------
# LLM instances (one per agent role) — via CrewAI native LLM class
# ---------------------------------------------------------------------------

master_llm = get_master_brain_llm()
coder_llm = get_coder_llm()
triage_llm = get_fast_triage_llm()
osint_llm = get_osint_llm()

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool("WebSearch")
def web_search(query: str) -> str:
    """Search the web for threat intelligence, CVEs, or IoCs."""
    try:
        from langchain_community.tools import DuckDuckGoSearchRun

        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as exc:
        logger.warning("Web search failed: %s", exc)
        return f"Search unavailable: {exc}"


@tool("HashFile")
def hash_file(content: str) -> str:
    """Return SHA256 hash of a string for integrity checks."""
    return hashlib.sha256(content.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Agent 1 — Threat Detection
# ---------------------------------------------------------------------------

threat_detection_agent = Agent(
    role="Threat Detection Specialist",
    goal="Classify raw SIEM alerts, map to MITRE ATT&CK techniques, and identify IOCs.",
    backstory="Expert SOC analyst with 15 years in threat intelligence and malware analysis. "
    "Specializes in mapping alerts to the MITRE ATT&CK framework.",
    llm=triage_llm,
    verbose=True,
    allow_delegation=False,
)

# ---------------------------------------------------------------------------
# Agent 2 — Risk Scoring
# ---------------------------------------------------------------------------

risk_scoring_agent = Agent(
    role="Risk Scoring Analyst",
    goal="Compute a quantitative risk score (0–100) with business impact assessment.",
    backstory="Senior risk analyst skilled in quantitative risk models (FAIR, ISO 27005). "
    "Assigns dollar-value impact estimates to every threat.",
    llm=triage_llm,
    verbose=True,
    allow_delegation=False,
)

# ---------------------------------------------------------------------------
# Agent 3 — Recommendation
# ---------------------------------------------------------------------------

recommendation_agent = Agent(
    role="SOAR Playbook Advisor",
    goal="Draft ISO 27001-aligned remediation actions and structured SOAR playbooks.",
    backstory="Ex-cybersecurity consultant who has built SOC runbooks for Fortune 500 companies. "
    "Outputs actionable steps with precise FortiGate CLI / API commands.",
    llm=coder_llm,
    verbose=True,
    allow_delegation=False,
)

# ---------------------------------------------------------------------------
# Agent 4 — Threat Hunter
# ---------------------------------------------------------------------------

threat_hunter_agent = Agent(
    role="Threat Hunter",
    goal="Proactively search for CVEs, IoCs, and threat reports related to the alert.",
    backstory="Former NSA threat hunter who tracks APT groups and zero-day campaigns. "
    "Uses open-source intelligence to enrich every alert with real-world context.",
    llm=osint_llm,
    verbose=True,
    allow_delegation=False,
    tools=[web_search],
)

# ---------------------------------------------------------------------------
# Agent 5 — Forensics
# ---------------------------------------------------------------------------

forensics_agent = Agent(
    role="Digital Forensics Analyst",
    goal="Query past incident memory (RAG) for similar threats and response patterns.",
    backstory="Forensic investigator with deep experience in incident response. "
    "Maintains a knowledge base of past attacks and their resolution playbooks.",
    llm=master_llm,
    verbose=True,
    allow_delegation=False,
)

# ---------------------------------------------------------------------------
# Agent 6 — Red Team
# ---------------------------------------------------------------------------

red_team_agent = Agent(
    role="Red Team Operator",
    goal="Simulate attacker paths and identify security gaps related to the alert.",
    backstory="Offensive security expert who thinks like a nation-state adversary. "
    "Maps potential attack chains and recommends defensive improvements.",
    llm=coder_llm,
    verbose=True,
    allow_delegation=False,
    tools=[web_search],
)

# ---------------------------------------------------------------------------
# Shared blackboard (Beehive)
# ---------------------------------------------------------------------------

import threading


class Beehive:
    """Thread-safe shared state for agent communication."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}

    def write(self, agent: str, key: str, value: Any) -> None:
        with self._lock:
            if agent not in self._data:
                self._data[agent] = {}
            self._data[agent][key] = value

    def read(self, agent: Optional[str] = None) -> dict[str, Any]:
        with self._lock:
            if agent:
                return dict(self._data.get(agent, {}))
            return {a: dict(v) for a, v in self._data.items()}

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


beehive = Beehive()


# ---------------------------------------------------------------------------
# Agent execution helpers
# ---------------------------------------------------------------------------

def run_agent_task(agent: Agent, task_description: str, context: Optional[str] = None) -> str:
    """Execute a single CrewAI agent task and return the result."""
    task = Task(
        description=task_description,
        agent=agent,
        expected_output="JSON-formatted analysis results",
        context=[{"role": "system", "content": context}] if context else None,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    return crew.kickoff()


def run_full_pipeline(raw_alert: dict) -> dict[str, Any]:
    """Run all 6 agents sequentially and return a consolidated decision package."""
    from datetime import datetime, timezone

    alert_json = json.dumps(raw_alert, indent=2)

    # 1. Threat Detection
    logger.info("[Agent 1/6] Threat Detection analyzing alert...")
    td_result = run_agent_task(
        threat_detection_agent,
        f"Classify this SIEM alert and map to MITRE ATT&CK:\n{alert_json}\n"
        "Output JSON with: threat_name, threat_category, mitre_technique_id, "
        "mitre_tactic, iocs (list of dicts with type and value), confidence (0-100).",
    )
    beehive.write("threat_detection", "result", td_result)

    # 2. Forensics (RAG query of past incidents)
    logger.info("[Agent 2/6] Forensics querying memory...")
    f_result = run_agent_task(
        forensics_agent,
        f"Based on alert context, analyze similar past incidents:\n{alert_json}\n"
        "Output JSON with: similar_incidents (list), recurrence_pattern, "
        "past_recommendations, lessons_learned.",
    )
    beehive.write("forensics", "result", f_result)

    # 3. Threat Hunter (web search)
    logger.info("[Agent 3/6] Threat Hunter searching IoCs...")
    th_result = run_agent_task(
        threat_hunter_agent,
        f"Research threat intelligence for:\n{alert_json}\n"
        "Use WebSearch tool. Output JSON with: cves (list), related_campaigns, "
        "ioc_enrichment, osint_notes.",
    )
    beehive.write("threat_hunter", "result", th_result)

    # 4. Risk Scoring
    logger.info("[Agent 4/6] Risk Scoring computing impact...")
    rs_result = run_agent_task(
        risk_scoring_agent,
        f"Assess business risk for this threat:\n{alert_json}\n"
        f"Forensics: {f_result}\nThreat Intel: {th_result}\n"
        "Output JSON with: risk_score (0-100), impact_level, financial_impact_usd, "
        "likelihood, affected_assets, regulatory_impact.",
    )
    beehive.write("risk_scoring", "result", rs_result)

    # 5. Recommendation
    logger.info("[Agent 5/6] Recommendation drafting playbook...")
    rec_result = run_agent_task(
        recommendation_agent,
        f"Create SOAR playbook for:\n{alert_json}\n"
        f"Risk: {rs_result}\n"
        "Output JSON with: recommended_action (block_ip|isolate_host|quarantine_file|investigate|no_action), "
        "playbook_steps (list), fortigate_commands, estimated_containment_minutes.",
    )
    beehive.write("recommendation", "result", rec_result)

    # 6. Red Team
    logger.info("[Agent 6/6] Red Team simulating attack paths...")
    rt_result = run_agent_task(
        red_team_agent,
        f"Simulate attack paths for this scenario:\n{alert_json}\n"
        f"Recommendation: {rec_result}\n"
        "Output JSON with: attack_paths (list), gaps_found (list), "
        "recommended_defenses (list), priority_level.",
    )
    beehive.write("red_team", "result", rt_result)

    # Compile final decision package
    decision = {
        "decision_id": f"DEC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{hashlib.md5(str(raw_alert).encode()).hexdigest()[:6]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "threat_name": json.loads(td_result if isinstance(td_result, str) else "{}").get("threat_name", "Unknown"),
        "mitre_technique": json.loads(td_result if isinstance(td_result, str) else "{}").get("mitre_technique_id", "T0000"),
        "risk_score": json.loads(rs_result if isinstance(rs_result, str) else "{}").get("risk_score", 50),
        "confidence": json.loads(td_result if isinstance(td_result, str) else "{}").get("confidence", 50),
        "recommended_action": json.loads(rec_result if isinstance(rec_result, str) else "{}").get("recommended_action", "investigate"),
        "iocs": json.loads(td_result if isinstance(td_result, str) else "{}").get("iocs", []),
        "playbook": json.loads(rec_result if isinstance(rec_result, str) else "{}").get("playbook_steps", []),
        "red_team_insights": json.loads(rt_result if isinstance(rt_result, str) else "{}").get("gaps_found", []),
        "agent_logs": beehive.read(),
    }

    beehive.clear()
    return decision
