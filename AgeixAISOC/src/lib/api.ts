/**
 * WP4 — AgeixAI Backend REST API Client
 *
 * All API calls go through this module. The frontend NEVER
 * calls the backend directly — this is the single integration boundary.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// ── Types ──────────────────────────────────────────────────────────────────

export interface WebhookAlert {
  rule_id: number
  src_ip: string
  dst_ip: string
  severity: "critical" | "high" | "medium" | "low"
  description: string
  agent_name: string
  raw_event: Record<string, unknown>
}

export interface EnrichmentResult {
  ioc: string
  ioc_type: "ip" | "hash" | "domain" | "url"
  reputation_score: number
  is_malicious: boolean
  country: string
  asn: string
  mitre_technique: string | null
  mitre_technique_name: string | null
  related_campaigns: string[]
  sources: string[]
  first_seen: string | null
  last_seen: string | null
  enrichment_timestamp: string
}

export interface DecisionPackage {
  package_id: string
  alert: WebhookAlert
  enrichment: EnrichmentResult | null
  risk_score: number
  risk_level: "low" | "medium" | "high" | "critical"
  ai_recommendation: string
  recommended_action: string
  iso_27001_ref: string | null
  nist_csf_ref: string | null
  requires_human_approval: boolean
  created_at: string
  osint_elevated?: boolean
  osint_context?: string
}

export interface DecisionResponse {
  status: string
  decision_id: string
  decision: string
  analyst_id: string
  notes: string
  rl_feedback: { feedback_id: string; delta: number }
  timestamp: string
}

export interface AuditEntry {
  id: string
  action_id: string
  action_type: string
  target: string
  source_agent: string
  decision: "pending" | "approved" | "rejected" | "modified"
  approved_by: string | null
  modification: string | null
  created_at: string
  reviewed_at: string | null
  previous_hash: string
  hash: string
}

export interface AuditTrailResponse {
  entries: AuditEntry[]
  total: number
  chain_integrity: boolean
}

export interface GapSignalResponse {
  status: string
  gap_id: string
  technique_id: string
  sigma_rule_id: string
  sigma_yaml: string
  message: string
}

// ── WebSocket Message Types ────────────────────────────────────────────────

export type WsMessageType =
  | "system_log"
  | "ai_decision"
  | "alert"
  | "hitl_request"
  | "hunt_result"
  | "rag_result"
  | "osint_report"
  | "darkweb_alert"
  | "pong"

export interface WsMessage {
  type: WsMessageType
  data?: Record<string, unknown>
  message?: string
  timestamp?: string
}

// ── API Client ─────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json()
}

/** POST /webhook/alert — send alert from WP1 */
export async function sendAlert(alert: WebhookAlert) {
  return apiFetch<{ status: string; package_id: string; message: string }>("/webhook/alert", {
    method: "POST",
    body: JSON.stringify(alert),
  })
}

/** GET /enrich/{ioc} — enrich IOC via WP2 */
export async function enrichIOC(ioc: string) {
  return apiFetch<EnrichmentResult>(`/enrich/${encodeURIComponent(ioc)}`)
}

/** POST /decision/{id} — human decision from WP3 */
export async function submitDecision(
  decisionId: string,
  decision: "approve" | "reject" | "modify",
  analystId: string = "human-analyst",
  notes: string = ""
) {
  return apiFetch<DecisionResponse>(`/decision/${decisionId}`, {
    method: "POST",
    body: JSON.stringify({ decision, analyst_id: analystId, notes }),
  })
}

/** POST /action/block — block IP at FortiGate (HITL-gated) */
export async function blockIP(
  decisionId: string,
  ipAddress: string,
  duration: string = "24h",
  reason: string = "AI-recommended block"
) {
  return apiFetch<{
    status: string
    rule_id: string
    ip_address: string
    duration: string
    message: string
    timestamp: string
  }>("/action/block", {
    method: "POST",
    body: JSON.stringify({ decision_id: decisionId, ip_address: ipAddress, duration, reason }),
  })
}

/** GET /api/hitl/audit — immutable audit trail */
export async function getAuditTrail(limit: number = 100, offset: number = 0) {
  return apiFetch<AuditTrailResponse>(`/api/hitl/audit?limit=${limit}&offset=${offset}`)
}

/** GET /api/hitl/verify — verify audit chain integrity */
export async function verifyAuditChain() {
  return apiFetch<{ status: string; chain_integrity: boolean; block_count: number }>("/api/hitl/verify")
}

/** POST /gap-loop/signal — trigger gap detection */
export async function triggerGapSignal(techniqueId: string, source: string = "manual") {
  return apiFetch<GapSignalResponse>("/gap-loop/signal", {
    method: "POST",
    body: JSON.stringify({ technique_id: techniqueId, source }),
  })
}

/** GET /api/health — backend health check */
export async function getHealth() {
  return apiFetch<{
    status: string
    version: string
    agents: string[]
    mcp_servers: string[]
    hitl_pending: number
    ws_clients: number
    timestamp: string
  }>("/api/health")
}

// ── Brain Stats ────────────────────────────────────────────────────────────

export interface HiveMindAgentActivity {
  status: "active" | "idle" | "inactive"
  action: string
  since: string
  idle_seconds: number
}

export interface AccuracyTrend {
  total_decisions: number
  matches: number
  mismatches: number
  undecided: number
  accuracy_pct: number
  recent_accuracy_pct: number
  trend: "improving" | "declining" | "stable"
  recent: Array<{
    decision_id: string
    ai_recommended: string
    human_decided: string
    matched: boolean | null
    timestamp: string
  }>
}

export interface BrainStatsResponse {
  status: string
  data: {
    hive_mind_activity: Record<string, HiveMindAgentActivity>
    hive_mind_agents: string[]
    current_cycle: number
    rag_memory_size: number
    rag_kb_count: number
    ai_accuracy_trend: AccuracyTrend
    rl_accuracy_score: number
    rl_feedback_events: number
    timestamp: string
  }
}

/** GET /api/brain-stats — Hive-Mind activity, RAG memory, accuracy trend */
export async function getBrainStats() {
  return apiFetch<BrainStatsResponse>("/api/brain-stats")
}


// ═══════════════════════════════════════════════════════════════════════════════
// Cyber Intelligence & Dark Web OSINT
// ═══════════════════════════════════════════════════════════════════════════════

export interface OsintDeepResearchRequest {
  target_name: string
  target_domain: string
}

export interface OsintDeepResearchResponse {
  status: string
  research_id: string
  message: string
  report?: Record<string, unknown>
}

export interface OsintResearchStatus {
  status: string
  research_id: string
  agents_completed: string[]
  all_agents_done: boolean
  report_ready: boolean
}

export interface DarkWebPasteAlert {
  id: string
  message: string
  source: string
  severity: string
  timestamp: string
}

/** POST /api/osint/deep-research — trigger OSINT Swarm */
export async function launchOsintDeepResearch(req: OsintDeepResearchRequest) {
  return apiFetch<OsintDeepResearchResponse>("/api/osint/deep-research", {
    method: "POST",
    body: JSON.stringify(req),
  })
}

/** GET /api/osint/status/{researchId} — check research progress */
export async function getOsintResearchStatus(researchId: string) {
  return apiFetch<OsintResearchStatus>(`/api/osint/status/${researchId}`)
}


// ═══════════════════════════════════════════════════════════════════════════════
// SOC Automation Hub — Phishing Triage & Honeypot
// ═══════════════════════════════════════════════════════════════════════════════

export interface PhishingTriageRequest {
  sender: string
  subject: string
  body: string
  attachment_urls?: string[]
  received_headers?: string[]
}

export interface PhishingTriageResponse {
  status: string
  analysis_id: string
  spoof_check: {
    spf_pass: boolean
    dkim_pass: boolean
    dmarc_pass: boolean
    domain: string
    sender_domain_age_days: number
    spoofed: boolean
    reason: string
  }
  url_analysis: Array<{
    url: string
    malicious_score: number
    categories: string[]
    detected_by: string[]
    reported_date: string
  }>
  extracted_iocs: Array<{
    ioc_type: string
    value: string
    context: string
  }>
  mitre_mappings: Array<{ id: string; name: string }>
  ir_report_draft: string
  risk_score: number
  requires_human_approval: boolean
  created_at: string
}

export interface CowrieAttackRequest {
  attacker_ip: string
  session_id?: string
  protocol?: "ssh" | "telnet" | "http"
  username_attempted?: string
  password_attempted?: string
  commands_executed?: string[]
  session_duration_seconds?: number
}

export interface CowrieAnalysisResponse {
  status: string
  analysis_id: string
  attacker_ip: string
  geoip: {
    ip: string
    country: string
    city: string
    isp: string
    asn: string
    proxy: boolean
    tor_exit_node: boolean
  }
  known_ttps: string[]
  threat_actor_profile: string
  sigma_rule_yaml: string
  sigma_rule_id: string
  saved_to_rag: boolean
  risk_score: number
  risk_level: string
  requires_human_approval: boolean
  created_at: string
}

/** POST /api/triage/phishing-email — full phishing analysis pipeline */
export async function launchPhishingTriage(req: PhishingTriageRequest) {
  return apiFetch<PhishingTriageResponse>("/api/triage/phishing-email", {
    method: "POST",
    body: JSON.stringify(req),
  })
}

/** POST /webhook/cowrie-attack — send Cowrie honeypot event */
export async function sendCowrieAttack(req: CowrieAttackRequest) {
  return apiFetch<CowrieAnalysisResponse>("/webhook/cowrie-attack", {
    method: "POST",
    body: JSON.stringify(req),
  })
}
