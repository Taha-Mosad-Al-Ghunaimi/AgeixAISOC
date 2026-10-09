from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Alert / Detection ───────────────────────────────────────────────────────

class Alert(BaseModel):
    id: str
    tenant_id: str = "demo"
    source: Literal["wazuh", "edr", "ndr", "forti", "sigma", "manual"]
    title: str
    description: str
    severity: Literal["critical", "high", "medium", "low"]
    mitre_attack_ids: list[str] = []
    raw_data: dict[str, Any] = {}
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TriageResult(BaseModel):
    alert_id: str
    tenant_id: str = "demo"
    verdict: Literal["true_positive", "false_positive", "suspicious"]
    mitre_mappings: list[dict[str, str]]
    priority_score: int = Field(ge=0, le=100)
    reasoning: str


# ── Risk Scoring ────────────────────────────────────────────────────────────

class RiskScoreRequest(BaseModel):
    alert_id: str
    asset_value: float = Field(default=1.0, ge=0)
    blast_radius_count: int = Field(default=0, ge=0)
    financial_impact_usd: float = Field(default=0.0, ge=0)
    public_exposure: bool = False
    regulatory: bool = False

class RiskScoreResponse(BaseModel):
    alert_id: str
    score: float = Field(ge=0, le=100)
    blast_radius_score: float = Field(ge=0, le=100)
    financial_score: float = Field(ge=0, le=100)
    regulatory_bonus: float = Field(ge=0, le=20)
    final_score: float = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high", "critical"]


# ── Recommendations / Playbooks ─────────────────────────────────────────────

class Recommendation(BaseModel):
    id: str
    playbook_id: str
    action: str
    target: str
    iso_27001_ref: str | None = None
    nist_csf_ref: str | None = None
    priority: Literal["urgent", "recommended", "optional"]
    reasoning: str


# ── Threat Hunting ──────────────────────────────────────────────────────────

class HuntQuery(BaseModel):
    id: str
    query_type: Literal["sigma", "kql", "spl", "yara", "osquery"]
    query: str
    time_range_hours: int = 24
    description: str

class HuntResult(BaseModel):
    query_id: str
    total_matches: int
    matches: list[dict[str, Any]]
    summary: str


# ── Red Team ────────────────────────────────────────────────────────────────

class ScanTarget(BaseModel):
    host: str
    ports: list[int] = Field(default_factory=lambda: [22, 80, 443, 445, 3306, 8080, 8443])

class CveMatch(BaseModel):
    cve_id: str
    service: str
    port: int
    cvss_score: float
    exploit_available: bool
    metasploit_module: str | None = None

class RedTeamReport(BaseModel):
    target: str
    open_ports: list[int]
    services: list[dict[str, Any]]
    cve_matches: list[CveMatch]
    exploit_simulation: str
    risk_summary: str


# ── Blue Team ───────────────────────────────────────────────────────────────

class WazuhWebhook(BaseModel):
    agent_id: str
    agent_name: str
    rule_id: int
    rule_description: str
    mitre_id: str | None = None
    severity: str
    timestamp: str

class InvestigationResult(BaseModel):
    webhook_id: str
    parallel_queries: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    verdict: str
    remediation_command: str | None = None


# ── MCP Server Responses ────────────────────────────────────────────────────

class McpQuery(BaseModel):
    server: str
    action: str
    params: dict[str, Any] = {}

class McpResponse(BaseModel):
    server: str
    action: str
    status: Literal["ok", "error"]
    data: list[dict[str, Any]] | dict[str, Any] | None = None
    error: str | None = None


# ── RAG ─────────────────────────────────────────────────────────────────────

class RagQuery(BaseModel):
    knowledge_base: Literal[
        "past_incidents", "threat_intel", "sigma_rules",
        "iso_27001", "cve_kev", "cmdb", "historical_logs",
        "learned_decisions", "external_threat_intel",
    ]
    query: str
    top_k: int = 5

class RagDocument(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any] = {}
    score: float

class RagResponse(BaseModel):
    knowledge_base: str
    query: str
    results: list[RagDocument]


# ── HITL ────────────────────────────────────────────────────────────────────

class SoarAction(BaseModel):
    action_id: str
    action_type: Literal["block_ip", "isolate_host", "deceive_attacker", "remediate", "kill_process", "update_rule", "xdr_isolate_host", "xdr_block_ip_fortigate"]
    target: str
    params: dict[str, Any] = {}
    source_agent: str
    reasoning: str

class HitlDecision(BaseModel):
    action_id: str
    status: Literal["pending", "approved", "rejected", "modified"]
    approved_by: str | None = None
    modification: str | None = None
    reviewed_at: str | None = None

class AuditLogEntry(BaseModel):
    id: str
    tenant_id: str = "demo"
    action_id: str
    action_type: str
    target: str
    source_agent: str
    decision: Literal["pending", "approved", "rejected", "modified"]
    approved_by: str | None = None
    modification: str | None = None
    created_at: str
    reviewed_at: str | None = None


# ── Orchestrator ────────────────────────────────────────────────────────────

class OrchestratorRequest(BaseModel):
    natural_language: str
    servers: list[str] = Field(default_factory=lambda: [
        "wazuh", "edr", "ndr", "red", "forti", "ti", "sigma", "rag", "forensics"
    ])

class OrchestratorResponse(BaseModel):
    query: str
    results: dict[str, McpResponse]
    summary: str


# ── Dashboard WebSocket ─────────────────────────────────────────────────────

class WsMessage(BaseModel):
    type: Literal["system_log", "ai_decision", "alert", "hitl_request", "remediation", "hunt_result"]
    data: dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ══════════════════════════════════════════════════════════════════════════════
# WP4 — Integration & AI Orchestration Contracts
# ══════════════════════════════════════════════════════════════════════════════

# ── POST /webhook/alert ─────────────────────────────────────────────────────

class WebhookAlert(BaseModel):
    """Inbound alert from WP1 (Wazuh)."""
    tenant_id: str = "demo"
    rule_id: int = Field(..., description="Wazuh rule ID that triggered")
    src_ip: str = Field(..., description="Source IP address")
    dst_ip: str = Field(..., description="Destination IP address")
    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="Alert severity")
    description: str = Field(default="", description="Human-readable alert description")
    agent_name: str = Field(default="unknown", description="Wazuh agent hostname")
    raw_event: dict[str, Any] = Field(default_factory=dict, description="Original Wazuh JSON event")


# ── GET /enrich/{ioc} ───────────────────────────────────────────────────────

class EnrichmentResult(BaseModel):
    """IP/Hash reputation + MITRE technique from WP2 (Threat Intel)."""
    tenant_id: str = "demo"
    ioc: str
    ioc_type: Literal["ip", "hash", "domain", "url"]
    reputation_score: float = Field(ge=0, le=100, description="0=clean, 100=malicious")
    is_malicious: bool
    country: str = Field(default="unknown")
    asn: str = Field(default="unknown")
    mitre_technique: str | None = Field(default=None, description="MITRE ATT&CK technique ID")
    mitre_technique_name: str | None = None
    related_campaigns: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list, description="Intel sources that flagged this IOC")
    first_seen: str | None = None
    last_seen: str | None = None
    enrichment_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── POST /decision/{id} ─────────────────────────────────────────────────────

class DecisionRequest(BaseModel):
    """Human decision from WP3 Dashboard — APPROVE / REJECT / MODIFY."""
    decision: Literal["approve", "reject", "modify"]
    analyst_id: str = Field(default="human-analyst", description="Analyst username or ID")
    notes: str = Field(default="", description="Optional notes or modification instructions")
    modification: dict[str, Any] | None = Field(default=None, description="Modified parameters if decision=modify")


# ── POST /action/block ──────────────────────────────────────────────────────

class ActionBlockRequest(BaseModel):
    """Block IP at FortiGate — ONLY executes after HITL approval."""
    decision_id: str = Field(..., description="ID of the approved human decision")
    ip_address: str = Field(..., description="IP to block at perimeter firewall")
    duration: str = Field(default="24h", description="Block duration: 1h, 24h, 7d, 30d, permanent")
    reason: str = Field(default="AI-recommended block after threat analysis")
    fortigate_profile: str = Field(default="default", description="FortiGate profile to apply rule to")


class ActionBlockResponse(BaseModel):
    status: str
    rule_id: str
    ip_address: str
    duration: str
    fortigate_profile: str
    message: str
    timestamp: str


# ── Decision Package (streamed via WS to WP3) ──────────────────────────────

class DecisionPackage(BaseModel):
    """
    The complete Decision Package broadcast to WP3 Dashboard.
    Contains: Alert + Enrichment + AI Risk Score + Recommendation.
    Every action requires human approval before execution.
    """
    package_id: str
    tenant_id: str = "demo"
    alert: WebhookAlert
    enrichment: EnrichmentResult | None = None
    risk_score: float = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high", "critical"]
    ai_recommendation: str
    recommended_action: str
    iso_27001_ref: str | None = None
    nist_csf_ref: str | None = None
    requires_human_approval: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    osint_elevated: bool = False
    osint_context: str | None = None


# ── Gap Signal (mock endpoint) ──────────────────────────────────────────────

class GapSignalRequest(BaseModel):
    """Mock gap signal — triggers Sigma rule generation."""
    technique_id: str = Field(..., description="MITRE ATT&CK technique ID, e.g. T1190")
    source: str = Field(default="manual", description="Source of the gap signal")
    description: str = Field(default="")


class GapSignalResponse(BaseModel):
    status: str
    gap_id: str
    technique_id: str
    sigma_rule_id: str
    sigma_yaml: str
    message: str


# ══════════════════════════════════════════════════════════════════════════════
# Hive-Mind / Adaptive RAG / Brain Stats
# ══════════════════════════════════════════════════════════════════════════════

class HiveMindActivity(BaseModel):
    agent: str
    status: str
    action: str
    since: str
    idle_seconds: float


class BrainStatsResponse(BaseModel):
    hive_mind_activity: dict[str, Any]
    hive_mind_agents: list[str]
    current_cycle: int
    rag_memory_size: int
    rag_kb_count: int
    ai_accuracy_trend: dict[str, Any]
    rl_accuracy_score: float
    rl_feedback_events: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LearnFromDecisionRequest(BaseModel):
    decision_id: str
    alert_context: dict[str, Any]
    ai_recommendation: str
    ai_recommended_action: str
    human_decision: str = Field(..., description="approve | reject | modify")
    human_notes: str = ""
    analyst_id: str = "human-analyst"
    mitre_techniques: list[str] = Field(default_factory=list)
    risk_score: float = 0.0
    risk_level: str = "medium"


# ══════════════════════════════════════════════════════════════════════════════
# Digital Forensics & Chain-of-Custody
# ══════════════════════════════════════════════════════════════════════════════

class EvidenceEntryResponse(BaseModel):
    entry_hash: str
    tenant_id: str = "demo"
    incident_id: str
    artifact_type: str
    agent_signature: str
    timestamp: str
    previous_hash: str
    content: dict[str, Any]


class ForensicsTimelineResponse(BaseModel):
    incident_id: str
    tenant_id: str = "demo"
    host: str = ""
    user: str = ""
    risk_score_at_collection: float = 0.0
    collected_by: str = "ageix-forensics-ai"
    collected_at: str = ""
    process_tree: list[dict[str, Any]] = Field(default_factory=list)
    network_connections: list[dict[str, Any]] = Field(default_factory=list)
    registry_changes: list[dict[str, Any]] = Field(default_factory=list)
    file_modifications: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    total_artifacts: int = 0
    forensics_skipped: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# Tier 1 SOC Automation: Phishing Analysis & Cloud Security
# ══════════════════════════════════════════════════════════════════════════════

class PhishingEmailPayload(BaseModel):
    sender: str = Field(..., description="From header email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Raw email body text")
    attachments: list[str] = Field(default_factory=list, description="Attachment filenames")
    attachment_urls: list[str] = Field(default_factory=list, description="URLs to download attachments")
    received_headers: list[str] = Field(default_factory=list, description="Received header lines for spoofing check")
    reply_to: str | None = Field(default=None, description="Reply-To header if present")


class PhishingIoc(BaseModel):
    ioc_type: Literal["ip", "hash", "domain", "url", "email"]
    value: str
    context: str = ""


class PhishingAnalysisResponse(BaseModel):
    status: str
    analysis_id: str
    spoof_check: dict[str, Any] = Field(default_factory=dict, description="SPF/DKIM/DMARC spoofing analysis")
    url_analysis: list[dict[str, Any]] = Field(default_factory=list, description="URL reputation results")
    extracted_iocs: list[PhishingIoc] = Field(default_factory=list)
    mitre_mappings: list[dict[str, str]] = Field(default_factory=list)
    ir_report_draft: str = Field(default="", description="Auto-generated Incident Response report")
    risk_score: float = Field(default=0.0, ge=0, le=100)
    requires_human_approval: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CloudTrailEvent(BaseModel):
    event_id: str
    event_name: str = Field(..., description="e.g. ConsoleLogin, PutBucketPolicy, AssumeRole")
    user_arn: str = Field(..., description="ARN of the IAM user/role that performed the action")
    source_ip: str = Field(..., description="Source IP address of the API call")
    user_agent: str = Field(default="", description="User-Agent string from the CloudTrail log")
    event_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    aws_region: str = Field(default="us-east-1")
    resources: list[dict[str, str]] = Field(default_factory=list, description="Affected AWS resources")
    request_params: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = Field(default=None, description="e.g. AccessDenied if present")


class CloudTrailAlert(BaseModel):
    tenant_id: str = "demo"
    trail_events: list[CloudTrailEvent] = Field(..., description="One or more CloudTrail log entries")
    anomaly_context: str = Field(default="", description="Optional context from GuardDuty or other sources")


class CloudTrailAnalysisResponse(BaseModel):
    status: str
    analysis_id: str
    threat_found: bool
    iam_abuse_type: str | None = Field(default=None, description="e.g. privilege_escalation, unauthorized_s3, anomaly_login")
    abuse_details: str = ""
    affected_user_arn: str = ""
    affected_resources: list[str] = Field(default_factory=list)
    mitre_mappings: list[dict[str, str]] = Field(default_factory=list)
    recommended_action: str = ""
    requires_human_approval: bool = True
    risk_score: float = Field(default=0.0, ge=0, le=100)
    risk_level: str = "low"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())



class ForensicsIncidentResponse(BaseModel):
    status: str
    incident_id: str
    tenant_id: str = "demo"
    timeline: ForensicsTimelineResponse | None = None
    evidence_chain: list[EvidenceEntryResponse] = Field(default_factory=list)
    chain_integrity: dict[str, Any] = {}


class ForensicsReportResponse(BaseModel):
    status: str
    incident_id: str
    tenant_id: str = "demo"
    report: dict[str, Any]


# ══════════════════════════════════════════════════════════════════════════════
# IOC Sweep & Threat Hunting
# ══════════════════════════════════════════════════════════════════════════════

class IocSweepRequest(BaseModel):
    iocs: list[str] = Field(..., description="List of IOCs: IPs, hashes, domains, URLs")
    actor_intel: bool = Field(default=True, description="Run STIX/TAXII actor matching on results")


class IocSweepMetrics(BaseModel):
    sweep_duration: str
    endpoints_scanned: int
    compromised_assets: int
    threat_actor_match_confidence: float


class IocSweepResponse(BaseModel):
    status: str
    tenant_id: str = "demo"
    data: dict[str, Any]
    metrics: IocSweepMetrics


# ══════════════════════════════════════════════════════════════════════════════
# Multi-Tenancy (SaaS)
# ══════════════════════════════════════════════════════════════════════════════

class TenantRegisterRequest(BaseModel):
    name: str = Field(..., description="Organization name")
    contact_email: str = Field(..., description="Admin email address")
    plan: Literal["starter", "pro", "enterprise"] = "starter"


class TenantRegisterResponse(BaseModel):
    tenant_id: str
    name: str
    plan: str
    api_key: str
    message: str


class TenantUsageResponse(BaseModel):
    tenant_id: str
    plan: str
    limits: dict[str, Any]
    current_usage: dict[str, Any]
    usage_percentages: dict[str, Any]


class TenantListResponse(BaseModel):
    tenants: list[dict[str, Any]]
    total: int


class AiTokensTrackRequest(BaseModel):
    tokens: int = Field(..., ge=0, description="Number of AI tokens consumed")


# ══════════════════════════════════════════════════════════════════════════════
# OSINT & Dark Web Swarm
# ══════════════════════════════════════════════════════════════════════════════

class OsintDeepResearchRequest(BaseModel):
    target_name: str = Field(..., description="Target organization name, e.g. 'Acme Security'")
    target_domain: str = Field(..., description="Target domain, e.g. 'acmesec.com'")


class OsintDeepResearchResponse(BaseModel):
    status: str
    research_id: str
    message: str
    report: dict[str, Any] | None = None


class DarkWebPasteAlert(BaseModel):
    id: str
    message: str
    source: str
    severity: str
    timestamp: str


class OsintResearchStatus(BaseModel):
    status: str
    research_id: str
    agents_completed: list[str]
    all_agents_done: bool
    report_ready: bool


# ══════════════════════════════════════════════════════════════════════════════
# PCAP / IDS Analysis (Network Traffic)
# ══════════════════════════════════════════════════════════════════════════════

class PcapEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_ip: str = Field(..., description="Source IP of the network event")
    dest_ip: str = Field(..., description="Destination IP")
    protocol: str = Field(default="TCP", description="Protocol: TCP, UDP, HTTP, DNS, TLS")
    alert_type: str = Field(..., description="e.g. sql_injection, nmap_scan, brute_force, c2_beacon, dns_tunnel")
    severity: Literal["critical", "high", "medium", "low", "info"] = "medium"
    payload_summary: str = Field(default="", description="Brief summary of the event payload")
    dst_port: int | None = Field(default=None)
    bytes_sent: int | None = Field(default=None)
    info: dict[str, Any] = Field(default_factory=dict)


class EndpointLogEntry(BaseModel):
    hostname: str
    event_id: str = ""
    description: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PcapSummaryRequest(BaseModel):
    tenant_id: str = "demo"
    pcap_events: list[PcapEvent] = Field(..., description="One or more Zeek / Suricata log entries")
    endpoint_logs: list[EndpointLogEntry] = Field(default_factory=list, description="Optional endpoint logs for correlation")


class PcapThreatFinding(BaseModel):
    threat_type: str = Field(..., description="Type of threat identified")
    source_ip: str = ""
    dest_ip: str = ""
    description: str = ""
    mitre_technique_id: str = ""
    mitre_technique_name: str = ""
    risk_score: float = 0.0


class PcapLateralMovementStep(BaseModel):
    step: int
    from_host: str = ""
    to_host: str = ""
    technique: str = ""
    evidence: str = ""
    timestamp: str = ""


class PcapSummaryResponse(BaseModel):
    status: str
    analysis_id: str
    total_events: int
    threats_found: list[PcapThreatFinding] = Field(default_factory=list)
    compromised_hosts: list[str] = Field(default_factory=list)
    lateral_movement_timeline: list[PcapLateralMovementStep] = Field(default_factory=list)
    isolation_recommendations: list[str] = Field(default_factory=list)
    risk_score: float = 0.0
    risk_level: str = "low"
    mitre_mappings: list[dict[str, str]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ══════════════════════════════════════════════════════════════════════════════
# Cowrie Honeypot Automation (Threat Intel + Sigma Rule + RAG)
# ══════════════════════════════════════════════════════════════════════════════

class CowrieAttack(BaseModel):
    tenant_id: str = "demo"
    attacker_ip: str = Field(..., description="Source IP of the attacker")
    session_id: str = Field(default="", description="Cowrie session identifier")
    protocol: Literal["ssh", "telnet", "http"] = "ssh"
    username_attempted: str = Field(default="root", description="Username attempted by attacker")
    password_attempted: str = Field(default="", description="Password attempted by attacker")
    commands_executed: list[str] = Field(default_factory=list, description="Commands executed inside the honeypot")
    session_duration_seconds: int = Field(default=0, description="Duration of the attacker session")
    downloaded_files: list[str] = Field(default_factory=list, description="Files downloaded by attacker")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CowrieAnalysisResponse(BaseModel):
    status: str
    analysis_id: str
    attacker_ip: str
    geoip: dict[str, Any] = Field(default_factory=dict)
    known_ttps: list[str] = Field(default_factory=list)
    threat_actor_profile: str = ""
    sigma_rule_yaml: str = ""
    sigma_rule_id: str = ""
    saved_to_rag: bool = False
    risk_score: float = 0.0
    risk_level: str = "medium"
    requires_human_approval: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ══════════════════════════════════════════════════════════════════════════════
# External Webhook (generic JSON alert ingestion)
# ══════════════════════════════════════════════════════════════════════════════

class ExternalWebhookAlert(BaseModel):
    """Generic inbound webhook alert from external sources (GitHub, CI/CD, scanners)."""
    source: str = Field(..., description="Source system, e.g. 'github_dependabot', 'snyk', 'jenkins', 'custom'")
    alert_type: str = Field(default="generic", description="Type of alert: vuln, breach, misconfig, anomaly")
    title: str = Field(default="", description="Short alert title")
    description: str = Field(default="", description="Detailed description")
    severity: Literal["critical", "high", "medium", "low", "info"] = Field(default="medium")
    ioc: str | None = Field(default=None, description="IP, hash, domain, or URL associated")
    target: str | None = Field(default=None, description="Affected target, e.g. repo name, host, user")
    raw_payload: dict[str, Any] = Field(default_factory=dict, description="Full original webhook body")


class ExternalWebhookResponse(BaseModel):
    status: str
    pipeline_id: str
    message: str
    risk_score: float | None = None


# ══════════════════════════════════════════════════════════════════════════════
# AI Exploit Prediction Engine — Vulnerability Management
# ══════════════════════════════════════════════════════════════════════════════

class VulnScanWebhook(BaseModel):
    """Inbound vulnerability scan result from OpenVAS / Nessus."""
    scanner: Literal["openvas", "nessus", "qualys", "rapid7", "custom"] = "openvas"
    cve_id: str = Field(..., description="CVE identifier, e.g. CVE-2025-44228")
    target_host: str = Field(default="", description="IP or hostname of the affected asset")
    port: int = Field(default=0, ge=0, le=65535, description="Affected port number")
    service: str = Field(default="", description="Service name on the affected port")
    cvss_score: float | None = Field(default=None, ge=0, le=10, description="Scanner-reported CVSS score (overrides database)")
    description: str = Field(default="", description="Scanner-provided description")
    tenant_id: str = "demo"


class PredictedVuln(BaseModel):
    """A single vulnerability with exploit prediction metadata."""
    vuln_id: str
    cve_id: str
    cvss: float
    cvss_severity: str
    description: str
    affected_software: str = ""
    affected_asset: str = ""
    port: int = 0
    service: str = ""
    published_date: str = ""
    vendor_patch_available: bool = False
    ransomware_associated: bool = False
    poc_exists: bool = False
    poc_source: str = ""
    poc_check_timestamp: str = ""
    risk_level: str = "medium"
    risk_elevated: bool = False
    risk_elevation_reason: str = ""
    exploit_likelihood: float = Field(default=0.0, ge=0, le=100, description="Exploit Likelihood score 0–100")
    exploit_likelihood_label: str = "low"
    ips_rule: str = ""
    ips_rule_generated: bool = False
    mitigation_recommended: str = ""
    requires_human_approval: bool = True
    scan_timestamp: str = ""


class VulnPredictedResponse(BaseModel):
    status: str
    total_vulns: int
    vulnerabilities: list[PredictedVuln] = Field(default_factory=list)
    statistics: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ══════════════════════════════════════════════════════════════════════════════
# Malware Triage & IOC Extractor
# ══════════════════════════════════════════════════════════════════════════════

class MalwareTriageIoc(BaseModel):
    ioc_type: Literal["ip", "domain", "hash", "filename", "registry", "mutex"]
    value: str
    context: str = ""


class MalwareTriageRequest(BaseModel):
    file_hash: str = Field(..., description="SHA-256 hash of the file to analyze")
    file_name: str | None = Field(default=None, description="Optional original file name")


class MalwareTriageResponse(BaseModel):
    analysis_id: str
    threat_name: str
    verdict: Literal["malicious", "suspicious", "clean", "unknown"]
    malicious_score: float = Field(ge=0, le=100)
    file_name: str = ""
    file_type: str = ""
    sandbox_source: str = ""
    analysis_date: str = ""
    extracted_iocs: list[MalwareTriageIoc] = Field(default_factory=list)
    auto_generated_yara: str = ""
    total_iocs: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    risk_level: str | None = None
