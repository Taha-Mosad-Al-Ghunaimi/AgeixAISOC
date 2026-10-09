"use client"

import { useState, useEffect, useCallback } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { launchPhishingTriage, type PhishingTriageResponse } from "@/lib/api"
import {
  Shield,
  Mail,
  Search,
  Globe,
  Activity,
  Clock,
  Users,
  FileText,
  Server,
  Cloud,
  BarChart3,
  Database,
  Bot,
  Skull,
  MousePointerClick,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Send,
  MoreHorizontal,
  Network,
  Cpu,
  Lock,
} from "lucide-react"

// ── Project Card ───────────────────────────────────────────────────────────

interface ProjectCardData {
  id: string
  title: string
  description: string
  icon: React.ElementType
  status: "idle" | "processing" | "pending_review"
  color: string
}

const PROJECTS: ProjectCardData[] = [
  { id: "phishing", title: "Phishing Triage", description: "Email header + URL analysis, IOC extraction", icon: Mail, status: "idle", color: "text-red-400" },
  { id: "pcap", title: "PCAP Analysis", description: "Zeek/Suricata event classification, lateral movement", icon: Network, status: "idle", color: "text-cyan-400" },
  { id: "cloud", title: "Cloud IAM Monitoring", description: "CloudTrail IAM abuse pattern detection", icon: Cloud, status: "idle", color: "text-blue-400" },
  { id: "honeypot", title: "Honeypot Intel", description: "Cowrie attack enrichment, Sigma rule generation", icon: Skull, status: "idle", color: "text-purple-400" },
  { id: "ioc", title: "IOC Enrichment", description: "IP/hash/domain reputation via Threat Intel", icon: Search, status: "idle", color: "text-emerald-400" },
  { id: "sigma", title: "Sigma Rule Gen", description: "Detection gap auto-generated Sigma YAML rules", icon: FileText, status: "idle", color: "text-amber-400" },
  { id: "ueba", title: "UEBA Anomaly", description: "User entity behavior analytics via ML", icon: Activity, status: "idle", color: "text-pink-400" },
  { id: "forensics", title: "Forensics Timeline", description: "WORM evidence chain, auto IR report", icon: Shield, status: "idle", color: "text-violet-400" },
  { id: "deception", title: "Deception Deploy", description: "Honeypot provisioning, attacker redirect", icon: Bot, status: "idle", color: "text-orange-400" },
  { id: "remediation", title: "Remediation Script", description: "Auto-generated fix scripts for vulns", icon: Cpu, status: "idle", color: "text-lime-400" },
]

const STATUS_STYLES = {
  idle: { label: "Idle", dot: "bg-zinc-600", badge: "bg-zinc-800/60 text-zinc-400 border-zinc-700/40" },
  processing: { label: "AI Processing", dot: "bg-amber-400 animate-pulse", badge: "bg-amber-600/20 text-amber-400 border-amber-700/30" },
  pending_review: { label: "Pending Human Review", dot: "bg-blue-400", badge: "bg-blue-600/20 text-blue-400 border-blue-700/30" },
}

function ProjectCard({ project, onActivate }: { project: ProjectCardData; onActivate: (id: string) => void }) {
  const Icon = project.icon
  const st = STATUS_STYLES[project.status]

  return (
    <button
      onClick={() => onActivate(project.id)}
      className="group relative flex flex-col items-start gap-3 rounded-xl border border-zinc-800/50 bg-zinc-900/40 p-4 text-left transition-all hover:border-zinc-700/60 hover:bg-zinc-800/40"
    >
      {/* Status badge */}
      <div className={cn("flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold", st.badge)}>
        <span className={cn("h-1.5 w-1.5 rounded-full", st.dot)} />
        {st.label}
      </div>

      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Icon className={cn("h-4 w-4", project.color)} />
          <span className="text-sm font-semibold text-zinc-200">{project.title}</span>
        </div>
        <p className="text-[11px] text-zinc-500 leading-relaxed">{project.description}</p>
      </div>
    </button>
  )
}

// ── Phishing Triage Interface ──────────────────────────────────────────────

function IOCBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800/40 bg-zinc-900/60 px-3 py-2">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">{label}</span>
      <p className="mt-0.5 text-xs font-mono font-medium text-zinc-300 truncate">{value}</p>
    </div>
  )
}

function PhishingTriageInterface() {
  const [emailText, setEmailText] = useState("")
  const [sender, setSender] = useState("")
  const [subject, setSubject] = useState("")
  const [urls, setUrls] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PhishingTriageResponse | null>(null)
  const [error, setError] = useState("")

  const handleTriage = useCallback(async () => {
    if (!emailText.trim()) return
    setLoading(true)
    setError("")
    setResult(null)
    try {
      const parsed = await launchPhishingTriage({
        sender: sender || "attacker@tempmail.com",
        subject: subject || "Urgent: Invoice",
        body: emailText,
        attachment_urls: urls ? urls.split("\n").map((u) => u.trim()).filter(Boolean) : [],
      })
      setResult(parsed)
    } catch (e: any) {
      setError(e.message || "API call failed. Is the backend running?")
    } finally {
      setLoading(false)
    }
  }, [emailText, sender, subject, urls])

  return (
    <div className="space-y-4">
      {/* Input */}
      <div className="rounded-xl border border-zinc-800/50 bg-zinc-900/40 p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Mail className="h-4 w-4 text-red-400" />
          <span className="text-sm font-semibold text-zinc-200">Paste Suspicious Email</span>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Sender</label>
            <input
              className="mt-1 w-full rounded-md border border-zinc-800/50 bg-zinc-950 px-3 py-1.5 text-xs text-zinc-300 placeholder-zinc-600"
              placeholder="sender@example.com"
              value={sender}
              onChange={(e) => setSender(e.target.value)}
            />
          </div>
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Subject</label>
            <input
              className="mt-1 w-full rounded-md border border-zinc-800/50 bg-zinc-950 px-3 py-1.5 text-xs text-zinc-300 placeholder-zinc-600"
              placeholder="Urgent: Invoice"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Attachment URLs</label>
            <input
              className="mt-1 w-full rounded-md border border-zinc-800/50 bg-zinc-950 px-3 py-1.5 text-xs text-zinc-300 placeholder-zinc-600"
              placeholder="One per line"
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
            />
          </div>
        </div>

        <Textarea
          rows={6}
          className="bg-zinc-950 border-zinc-800/50 text-zinc-300 text-xs font-mono placeholder-zinc-600"
          placeholder={`Paste the full email body here...\n\nExample:\nFrom: security@bankofamerica-secure.com\nSubject: Urgent: Account Suspended\nBody: Dear customer, your account has been suspended...`}
          value={emailText}
          onChange={(e) => setEmailText(e.target.value)}
        />

        <Button
          size="sm"
          onClick={handleTriage}
          disabled={loading || !emailText.trim()}
          className="gap-1.5 bg-red-600 hover:bg-red-500 text-white"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
          {loading ? "AgeixAI Triaging..." : "Triage with AgeixAI"}
        </Button>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-800/30 bg-red-900/10 px-3 py-2">
            <AlertTriangle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
            <span className="text-[11px] text-red-400">{error}</span>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-3">
          {/* Spoof Check + Risk */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div className="rounded-lg border border-zinc-800/40 bg-zinc-900/60 px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">SPF</span>
              <p className={cn("mt-0.5 text-xs font-bold", result.spoof_check.spf_pass ? "text-emerald-400" : "text-red-400")}>
                {result.spoof_check.spf_pass ? "PASS" : "FAIL"}
              </p>
            </div>
            <div className="rounded-lg border border-zinc-800/40 bg-zinc-900/60 px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">DKIM</span>
              <p className={cn("mt-0.5 text-xs font-bold", result.spoof_check.dkim_pass ? "text-emerald-400" : "text-red-400")}>
                {result.spoof_check.dkim_pass ? "PASS" : "FAIL"}
              </p>
            </div>
            <div className="rounded-lg border border-zinc-800/40 bg-zinc-900/60 px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">DMARC</span>
              <p className={cn("mt-0.5 text-xs font-bold", result.spoof_check.dmarc_pass ? "text-emerald-400" : "text-red-400")}>
                {result.spoof_check.dmarc_pass ? "PASS" : "FAIL"}
              </p>
            </div>
            <div className="rounded-lg border border-zinc-800/40 bg-zinc-900/60 px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Risk Score</span>
              <p className={cn("mt-0.5 text-lg font-bold", result.risk_score >= 60 ? "text-red-400" : result.risk_score >= 30 ? "text-amber-400" : "text-emerald-400")}>
                {result.risk_score}/100
              </p>
            </div>
          </div>

          {/* Extracted IOCs */}
          {result.extracted_iocs.length > 0 && (
            <div className="rounded-xl border border-zinc-800/50 bg-zinc-900/40 p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                <span className="text-sm font-semibold text-zinc-200">Extracted IOCs ({result.extracted_iocs.length})</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {result.extracted_iocs.map((ioc: any, i: number) => (
                  <IOCBadge key={i} label={ioc.ioc_type.toUpperCase()} value={ioc.value} />
                ))}
              </div>
            </div>
          )}

          {/* Malicious URLs */}
          {result.url_analysis.length > 0 && (
            <div className="rounded-xl border border-zinc-800/50 bg-zinc-900/40 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Globe className="h-4 w-4 text-red-400" />
                <span className="text-sm font-semibold text-zinc-200">URL Analysis</span>
              </div>
              <div className="space-y-2">
                {result.url_analysis.map((ua: any, i: number) => (
                  <div key={i} className="flex items-center justify-between rounded-lg border border-zinc-800/30 bg-zinc-950/60 px-3 py-2">
                    <span className="text-xs font-mono text-zinc-300 truncate max-w-[60%]">{ua.url}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={ua.malicious_score >= 50 ? "destructive" : "secondary"} className="text-[10px]">
                        {ua.malicious_score}/100
                      </Badge>
                      {ua.categories?.map((cat: string, j: number) => (
                        <span key={j} className="text-[10px] text-zinc-600">{cat}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* IR Report */}
          {result.ir_report_draft && (
            <div className="rounded-xl border border-zinc-800/50 bg-zinc-900/40 p-4">
              <div className="flex items-center gap-2 mb-3">
                <FileText className="h-4 w-4 text-cyan-400" />
                <span className="text-sm font-semibold text-zinc-200">Auto-Generated IR Report</span>
                <Badge variant="outline" className="text-[10px] text-cyan-400 border-cyan-800/30 ml-auto">AI DRAFT</Badge>
              </div>
              <ScrollArea className="h-[300px]">
                <pre className="text-[11px] font-mono text-zinc-400 whitespace-pre-wrap leading-relaxed">{result.ir_report_draft}</pre>
              </ScrollArea>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Honeypot Live Intel Map ────────────────────────────────────────────────

interface AttackerEntry {
  ip: string
  country: string
  city: string
  ttps: string[]
  risk_score: number
  timestamp: string
  x: number
  y: number
}

function HoneypotIntelMap() {
  const [attackers, setAttackers] = useState<AttackerEntry[]>([])
  const [hoveredIp, setHoveredIp] = useState<string | null>(null)

  // Simulate incoming attacks
  useEffect(() => {
    const countries = [
      { country: "Russia", city: "Moscow", baseX: 25, baseY: 30 },
      { country: "China", city: "Beijing", baseX: 75, baseY: 25 },
      { country: "Iran", city: "Tehran", baseX: 45, baseY: 35 },
      { country: "North Korea", city: "Pyongyang", baseX: 72, baseY: 28 },
      { country: "Brazil", city: "Sao Paulo", baseX: 40, baseY: 70 },
      { country: "India", city: "Mumbai", baseX: 68, baseY: 40 },
    ]
    const ttpSets = [
      ["Brute Force", "SSH Scanning"],
      ["Brute Force", "Credential Access", "Lateral Movement"],
      ["Port Scanning", "Service Discovery"],
      ["C2 Beaconing", "DNS Tunneling"],
      ["Web App Scanning", "SQL Injection"],
    ]

    const interval = setInterval(() => {
      const geo = countries[Math.floor(Math.random() * countries.length)]
      const ttp = ttpSets[Math.floor(Math.random() * ttpSets.length)]
      const ip = `${Math.floor(Math.random() * 223) + 1}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`

      setAttackers((prev) => [
        {
          ip,
          country: geo.country,
          city: geo.city,
          ttps: ttp,
          risk_score: Math.floor(30 + Math.random() * 70),
          timestamp: new Date().toISOString(),
          x: geo.baseX + (Math.random() - 0.5) * 10,
          y: geo.baseY + (Math.random() - 0.5) * 10,
        },
        ...prev.slice(0, 19),
      ])
    }, 4000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="rounded-xl border border-zinc-800/50 bg-zinc-900/40 p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Skull className="h-4 w-4 text-purple-400" />
          <span className="text-sm font-semibold text-zinc-200">Honeypot Live Intel Map — VLAN 30</span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-zinc-600">
          <span className="flex h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
          {attackers.length} attacks
        </div>
      </div>

      {/* Visual radar map */}
      <div className="relative h-[300px] rounded-lg border border-zinc-800/30 bg-[#0a0a0b] overflow-hidden">
        {/* Grid lines */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          <line x1="0" y1="50" x2="100" y2="50" stroke="rgb(39,39,42)" strokeWidth="0.3" />
          <line x1="50" y1="0" x2="50" y2="100" stroke="rgb(39,39,42)" strokeWidth="0.3" />
          <circle cx="50" cy="50" r="25" fill="none" stroke="rgb(39,39,42)" strokeWidth="0.3" />
          <circle cx="50" cy="50" r="45" fill="none" stroke="rgb(39,39,42)" strokeWidth="0.3" />
          {/* Labels */}
          <text x="50" y="8" textAnchor="middle" fill="rgb(63,63,70)" fontSize="2.5">VLAN 30 — Cowrie Honeypot</text>
          <text x="50" y="96" textAnchor="middle" fill="rgb(63,63,70)" fontSize="2">Attacks geo-mapped by source country</text>
        </svg>

        {/* Attacker dots */}
        {attackers.map((a, i) => {
          const isHovered = hoveredIp === a.ip
          const size = Math.min(6 + a.risk_score / 25, 10)
          return (
            <div key={`${a.ip}-${i}`} style={{ position: "absolute", left: `${a.x}%`, top: `${a.y}%` }}>
              <div
                className="absolute rounded-full bg-red-500/80 cursor-pointer transition-all hover:scale-150"
                style={{ width: size, height: size, transform: "translate(-50%, -50%)" }}
                onMouseEnter={() => setHoveredIp(a.ip)}
                onMouseLeave={() => setHoveredIp(null)}
              />
              {isHovered && (
                <div className="absolute z-10 w-56 -translate-x-1/2 translate-y-2 rounded-lg border border-zinc-700/50 bg-zinc-900/95 p-3 shadow-xl backdrop-blur">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-zinc-200 font-mono">{a.ip}</span>
                    <Badge variant="destructive" className="text-[9px]">{a.risk_score}</Badge>
                  </div>
                  <div className="space-y-0.5 text-[10px] text-zinc-500">
                    <p>Country: <span className="text-zinc-300 font-medium">{a.country}</span></p>
                    <p>City: <span className="text-zinc-300 font-medium">{a.city}</span></p>
                    <p>TTPs: <span className="text-zinc-300">{a.ttps.join(", ")}</span></p>
                    <p className="text-[9px] text-zinc-700 mt-1">
                      {new Date(a.timestamp).toLocaleTimeString("en-US", { hour12: false })}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {/* No attacks state */}
        {attackers.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-xs text-zinc-700 italic">Waiting for Cowrie honeypot attacks...</p>
          </div>
        )}
      </div>

      {/* Recent attackers strip */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {attackers.slice(0, 8).map((a, i) => (
          <Badge
            key={i}
            variant="outline"
            className={cn(
              "gap-1.5 text-[10px] font-mono border-zinc-700/40 cursor-default",
              a.risk_score >= 70 ? "text-red-400" : a.risk_score >= 50 ? "text-amber-400" : "text-zinc-400",
            )}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
            {a.ip}
          </Badge>
        ))}
      </div>
    </div>
  )
}

// ── Automation ROI Widget ─────────────────────────────────────────────────

function AutomationRoiWidget() {
  const [metrics, setMetrics] = useState({ decisions: 0, hoursSaved: 0 })

  useEffect(() => {
    // Start with realistic mock values
    let count = 47
    setMetrics({ decisions: count, hoursSaved: Math.round(count * 0.5) })

    const interval = setInterval(() => {
      count += Math.floor(Math.random() * 3) + 1
      setMetrics({ decisions: count, hoursSaved: Math.round(count * 0.5) })
    }, 8000)

    return () => clearInterval(interval)
  }, [])

  // Derived metrics
  const avgResponseTimeMin = 47
  const humanTimePerDecision = 30
  const teamProductivityPct = Math.min(Math.round((1 - avgResponseTimeMin / humanTimePerDecision) * 100), 95)

  return (
    <div className="rounded-xl border border-emerald-800/30 bg-gradient-to-br from-emerald-950/40 to-zinc-900/40 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600/20 border border-emerald-700/30">
          <BarChart3 className="h-5 w-5 text-emerald-400" />
        </div>
        <div>
          <span className="text-sm font-bold text-zinc-200">Automation ROI</span>
          <p className="text-[11px] text-zinc-500">Tier 1 SOC productivity impact</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main metric */}
        <div className="col-span-1 md:col-span-2">
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold tracking-tight text-emerald-400">
              {metrics.hoursSaved}
            </span>
            <span className="text-sm text-zinc-500 font-medium">hours</span>
          </div>
          <p className="mt-1.5 text-sm text-zinc-400">
            AgeixAI saved analysts <span className="font-semibold text-emerald-400">{metrics.hoursSaved} hours</span> this week
            by automating <span className="font-semibold text-emerald-400">{metrics.decisions} Tier 1/2 decisions</span>.
          </p>
          <div className="mt-4 flex items-center gap-2 text-[11px] text-zinc-600">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            Avg {avgResponseTimeMin}m AI response vs {humanTimePerDecision}m human
          </div>
        </div>

        {/* Side stats */}
        <div className="space-y-3">
          <div className="rounded-lg border border-zinc-800/30 bg-zinc-900/60 px-4 py-3">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600">AI Decisions</span>
            <p className="text-2xl font-bold text-zinc-200 mt-1">{metrics.decisions}</p>
          </div>
          <div className="rounded-lg border border-zinc-800/30 bg-zinc-900/60 px-4 py-3">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600">Team Productivity</span>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{teamProductivityPct}%</p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────

export function SocAutomationHub() {
  const [projects, setProjects] = useState(PROJECTS)
  const [activeSection, setActiveSection] = useState<string | null>(null)

  const handleActivate = useCallback((id: string) => {
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, status: "processing" as const } : p)))
    setActiveSection(id)

    // Simulate AI processing, then move to pending review
    setTimeout(() => {
      setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, status: "pending_review" as const } : p)))
    }, 3000)
  }, [])

  return (
    <div className="space-y-8">
      {/* 4. ROI Widget (top) */}
      <AutomationRoiWidget />

      {/* 1. Automated Projects Grid */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Bot className="h-5 w-5 text-zinc-400" />
          <h2 className="text-lg font-bold text-zinc-200">Automated Tier 1/2 SOC Projects</h2>
          <span className="text-[10px] text-zinc-600 font-mono ml-auto">
            {projects.filter((p) => p.status !== "idle").length} active
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {projects.map((p) => (
            <ProjectCard key={p.id} project={p} onActivate={handleActivate} />
          ))}
        </div>
      </div>

      {/* 2. Phishing Triage Interface */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Mail className="h-5 w-5 text-red-400" />
          <h2 className="text-lg font-bold text-zinc-200">Phishing Triage Interface</h2>
          <Badge variant="outline" className="text-[10px] text-red-400 border-red-800/30 ml-auto">LIVE</Badge>
        </div>
        <PhishingTriageInterface />
      </div>

      {/* 3. Honeypot Live Intel Map */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Skull className="h-5 w-5 text-purple-400" />
          <h2 className="text-lg font-bold text-zinc-200">Honeypot Live Intel Map — VLAN 30</h2>
          <Badge variant="default" className="text-[10px] text-purple-400 border-purple-800/30 bg-purple-600/10 ml-auto">STREAMING</Badge>
        </div>
        <HoneypotIntelMap />
      </div>
    </div>
  )
}
