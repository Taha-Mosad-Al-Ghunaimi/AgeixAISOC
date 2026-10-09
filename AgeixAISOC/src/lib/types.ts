export type PlanTier = "Starter" | "Pro" | "Enterprise"

export type Tenant = {
  id: string
  name: string
  plan: PlanTier
  active: boolean
}

export type DecisionStatus = "Pending" | "Approved" | "Rejected" | "Modified"

export type Severity = "Critical" | "High" | "Medium" | "Low"

export type AlertSource = "Wazuh" | "Zeek" | "FortiGate" | "CrowdStrike" | "SentinelOne"

export type MITRETactic =
  | "Reconnaissance"
  | "Resource Development"
  | "Initial Access"
  | "Execution"
  | "Persistence"
  | "Privilege Escalation"
  | "Defense Evasion"
  | "Credential Access"
  | "Discovery"
  | "Lateral Movement"
  | "Collection"
  | "Command and Control"
  | "Exfiltration"
  | "Impact"

export type AIAgent = "Threat Detection" | "Risk Scoring" | "Recommendation" | "Threat Hunter" | "Red Team" | "Forensics"

export type PendingDecision = {
  id: string
  timestamp: string
  title: string
  description: string
  riskScore: number
  severity: Severity
  source: AlertSource
  mitreTactic: MITRETactic
  mitreTechnique: string
  affectedHost: string
  affectedIP: string
  recommendedAction: string
  status: DecisionStatus
  analyst?: string
  decisionTime?: string
  notes?: string
}

export type Incident = {
  id: string
  title: string
  severity: Severity
  status: "Active" | "Contained" | "Resolved" | "Investigating"
  startedAt: string
  updatedAt: string
  mitreTactic: MITRETactic
  mitreTechnique: string
  affectedHosts: string[]
  forensicArtifacts: ForensicArtifact[]
  timeline: IncidentEvent[]
}

export type IncidentEvent = {
  timestamp: string
  agent: AIAgent
  action: string
  detail: string
}

export type ForensicArtifact = {
  id: string
  type: "Process" | "Network" | "File" | "Registry" | "Memory" | "Disk"
  name: string
  path?: string
  hash?: string
  collectedAt: string
  collectedBy: AIAgent
  relevance: string
}

export type AgentStatus = {
  agent: AIAgent
  status: "Active" | "Analyzing" | "Idle" | "Error"
  currentTask: string
  lastActive: string
  accuracy: number
  tasksCompleted: number
}

export type DetectionGap = {
  id: string
  attackTechnique: string
  detected: boolean
  sigmaGenerated: boolean
  sigmaRule?: string
  ruleName?: string
  humanApproved: boolean
  deployed: boolean
  discoveredAt: string
}

export type IOC = {
  id: string
  type: "IP" | "Domain" | "URL" | "Hash" | "Email"
  value: string
  source: "VirusTotal" | "AbuseIPDB" | "AlienVault OTX" | "MISP" | "ThreatFox"
  confidence: number
  severity: Severity
  firstSeen: string
  lastSeen: string
  tags: string[]
}

export type AuditEntry = {
  id: string
  timestamp: string
  decisionId: string
  analystId: string
  analystName: string
  action: DecisionStatus
  title: string
  originalRecommendation: string
  modifiedAction?: string
  notes?: string
  immutableHash: string
  blockNumber: number
}
