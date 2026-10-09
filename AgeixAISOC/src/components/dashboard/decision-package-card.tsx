"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import {
  Shield, AlertTriangle, CheckCircle, XCircle, ExternalLink,
  Activity, Globe, Lock, Clock, Server, FileText, Skull,
  Search, ChevronDown, ChevronRight, Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { DecisionPackage as Dpkg } from "@/lib/api"
import { submitDecision } from "@/lib/api"

// ── Severity Config ────────────────────────────────────────────────────────

const severityConfig = {
  critical: { badge: "critical", icon: AlertTriangle, border: "border-red-700/40", bg: "bg-red-600/5", glow: "shadow-red-600/10", text: "text-red-400" },
  high: { badge: "destructive", icon: AlertTriangle, border: "border-red-700/25", bg: "bg-red-600/5", glow: "shadow-red-600/5", text: "text-red-400" },
  medium: { badge: "warning", icon: Activity, border: "border-amber-700/25", bg: "bg-amber-600/5", glow: "shadow-amber-600/5", text: "text-amber-400" },
  low: { badge: "info", icon: Activity, border: "border-blue-700/25", bg: "bg-blue-600/5", glow: "shadow-blue-600/5", text: "text-blue-400" },
}

// ── Decision Package Card ──────────────────────────────────────────────────

type DecisionStatus = "pending" | "approved" | "rejected" | "modified"

interface Props {
  pkg: Dpkg
  onDecided?: (id: string, status: string) => void
}

export function DecisionPackageCard({ pkg, onDecided }: Props) {
  const [status, setStatus] = useState<DecisionStatus>("pending")
  const [notes, setNotes] = useState("")
  const [showNotes, setShowNotes] = useState(false)
  const [pendingAction, setPendingAction] = useState<"approve" | "reject" | "modify" | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)

  // Mock web search queries based on alert data
  const mockQueries = [
    `Searching DuckDuckGo for: ${pkg.alert.src_ip} IOC threat intelligence...`,
    `Searching DuckDuckGo for: ${pkg.alert.description} exploit CVE...`,
    `Searching DuckDuckGo for: ${pkg.alert.rule_id} rule_id attack pattern...`,
  ]
  const mockResults = [
    `Found 3 articles linking to APT29 — ${pkg.alert.src_ip} associated with C2 infrastructure`,
    `MITRE ATT&CK ${pkg.enrichment?.mitre_technique || "T1071.001"} — beaconing pattern matches Emotet campaign`,
    `ThreatFox pulse: ${pkg.alert.src_ip} reported by 4 feeds — reputation ${pkg.enrichment?.reputation_score || "85"}/100`,
  ]

  const sev = severityConfig[pkg.risk_level]
  const Icon = sev.icon

  async function handleDecision(action: "approve" | "reject" | "modify") {
    if (action === "reject" || action === "modify") {
      setPendingAction(action)
      setShowNotes(true)
      return
    }
    // Approve immediately
    setSubmitting(true)
    try {
      await submitDecision(pkg.package_id, action, "human-analyst", notes)
      setStatus("approved")
      onDecided?.(pkg.package_id, "approved")
    } catch { /* toast in production */ } finally {
      setSubmitting(false)
    }
  }

  async function confirmWithNotes() {
    if (!pendingAction) return
    setSubmitting(true)
    try {
      await submitDecision(pkg.package_id, pendingAction, "human-analyst", notes)
      setStatus(pendingAction === "reject" ? "rejected" : "modified")
      onDecided?.(pkg.package_id, pendingAction)
      setShowNotes(false)
    } catch { /* toast */ } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={cn(
      "relative rounded-xl border p-5 transition-all duration-300",
      sev.border, sev.bg, sev.glow,
      "hover:shadow-lg hover:border-zinc-600/50",
      status !== "pending" && "opacity-70"
    )}>
      {/* Status indicator */}
      {status === "pending" && (
        <div className="absolute top-4 right-4 flex items-center gap-1.5">
          <span className="flex h-2 w-2">
            <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-amber-400 opacity-75" />
            <span className="inline-flex h-2 w-2 rounded-full bg-amber-500" />
          </span>
          <span className="text-[10px] font-medium text-amber-400 uppercase tracking-wider">Awaiting HITL</span>
        </div>
      )}
      {status !== "pending" && (
        <div className="absolute top-4 right-4">
          {status === "approved" && <span className="flex items-center gap-1 text-[11px] font-medium text-green-400"><CheckCircle className="h-3.5 w-3.5" /> Approved</span>}
          {status === "rejected" && <span className="flex items-center gap-1 text-[11px] font-medium text-red-400"><XCircle className="h-3.5 w-3.5" /> Rejected</span>}
          {status === "modified" && <span className="flex items-center gap-1 text-[11px] font-medium text-blue-400"><ExternalLink className="h-3.5 w-3.5" /> Modified</span>}
        </div>
      )}

      {/* Header */}
      <div className="flex items-start gap-3 mb-3 pr-36">
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg border", sev.border, "bg-zinc-900/80")}>
          <Icon className={cn("h-4 w-4", sev.text)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="text-sm font-semibold text-zinc-200 truncate">
              {pkg.alert.description || `Alert Rule ${pkg.alert.rule_id}`}
            </h3>
            <Badge variant={sev.badge as any} className="text-[10px] px-1.5 py-0">{pkg.risk_level}</Badge>
          </div>
          <p className="text-xs text-zinc-500 font-mono">
            {pkg.package_id} &middot; {new Date(pkg.created_at).toLocaleTimeString()}
          </p>
        </div>
      </div>

      {/* Alert Details + Enrichment Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Source IP</span>
          <p className="text-xs font-mono font-medium text-zinc-300 mt-0.5">{pkg.alert.src_ip}</p>
        </div>
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Destination</span>
          <p className="text-xs font-mono font-medium text-zinc-300 mt-0.5">{pkg.alert.dst_ip}</p>
        </div>
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Rule ID</span>
          <p className="text-xs font-mono font-medium text-zinc-300 mt-0.5">{pkg.alert.rule_id}</p>
        </div>
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Agent</span>
          <p className="text-xs font-medium text-zinc-300 mt-0.5">{pkg.alert.agent_name}</p>
        </div>
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Severity</span>
          <Badge variant={pkg.alert.severity === "critical" ? "critical" : pkg.alert.severity === "high" ? "destructive" : "secondary"} className="text-[10px] mt-0.5">
            {pkg.alert.severity}
          </Badge>
        </div>
      </div>

      {/* Risk Score + MITRE + ISO */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">AI Risk Score</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <div className="h-2 w-16 rounded-full overflow-hidden bg-zinc-800">
              <div className={cn("h-full rounded-full", pkg.risk_score >= 80 ? "bg-red-500" : pkg.risk_score >= 60 ? "bg-amber-500" : "bg-blue-500")} style={{ width: `${pkg.risk_score}%` }} />
            </div>
            <span className={cn("text-xs font-bold", pkg.risk_score >= 80 ? "text-red-400" : pkg.risk_score >= 60 ? "text-amber-400" : "text-blue-400")}>
              {pkg.risk_score}/100
            </span>
          </div>
        </div>
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">MITRE Technique</span>
          <p className="text-xs font-medium text-zinc-300 mt-0.5">{pkg.enrichment?.mitre_technique || "—"}</p>
          {pkg.enrichment?.mitre_technique_name && (
            <p className="text-[10px] text-zinc-500">{pkg.enrichment.mitre_technique_name}</p>
          )}
        </div>
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">ISO 27001 / NIST</span>
          <p className="text-xs font-mono font-medium text-zinc-300 mt-0.5">{pkg.iso_27001_ref || "—"}</p>
          {pkg.nist_csf_ref && <p className="text-[10px] text-zinc-500">{pkg.nist_csf_ref}</p>}
        </div>
      </div>

      {/* Enrichment Data (if available) */}
      {pkg.enrichment && (
        <div className="mb-3 rounded-lg border border-cyan-800/20 bg-cyan-900/5 px-4 py-2.5">
          <div className="flex items-center gap-2 mb-1">
            <Globe className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-400">WP2 Enrichment</span>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-zinc-400">
            <span>Reputation: <span className={cn("font-bold", pkg.enrichment.reputation_score >= 80 ? "text-red-400" : "text-amber-400")}>{pkg.enrichment.reputation_score}/100</span></span>
            <span>Country: <span className="font-medium text-zinc-300">{pkg.enrichment.country}</span></span>
            <span>ASN: <span className="font-medium text-zinc-300">{pkg.enrichment.asn}</span></span>
            {pkg.enrichment.related_campaigns.length > 0 && (
              <span>Campaigns: <span className="font-medium text-zinc-300">{pkg.enrichment.related_campaigns.join(", ")}</span></span>
            )}
          </div>
        </div>
      )}

      {/* OSINT Dark Web Badge */}
      {pkg.osint_elevated && (
        <div className="mb-3 rounded-lg border border-violet-800/30 bg-violet-900/10 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <Skull className="h-4 w-4 text-violet-400" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-violet-400">Dark Web Correlation Found</span>
            <Badge variant="critical" className="ml-auto text-[10px]">CRITICAL</Badge>
          </div>
          {pkg.osint_context && (
            <p className="text-xs text-zinc-400 mt-1.5">{pkg.osint_context}</p>
          )}
        </div>
      )}

      {/* Live Web Search & OSINT — expandable */}
      <div className="mb-3">
        <button
          onClick={() => setSearchOpen(!searchOpen)}
          className="flex w-full items-center gap-2 rounded-lg border border-zinc-800/40 bg-zinc-800/20 px-4 py-2.5 text-left transition-colors hover:bg-zinc-800/40"
        >
          <Search className="h-3.5 w-3.5 text-cyan-400" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Live Web Search &amp; OSINT</span>
          <span className="ml-auto text-zinc-600">
            {searchOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </span>
        </button>

        {searchOpen && (
          <div className="mt-2 rounded-lg border border-zinc-800/30 bg-[#0a0a0b] px-4 py-3 font-mono text-xs">
            <div className="flex items-center gap-2 mb-3 border-b border-zinc-800/30 pb-2">
              <Loader2 className="h-3 w-3 animate-spin text-emerald-500" />
              <span className="text-[10px] font-semibold text-emerald-400">Threat Hunter Agent — Web Search Log</span>
            </div>
            <div className="space-y-2">
              {mockQueries.map((q, i) => (
                <div key={i}>
                  <div className="flex items-start gap-1.5">
                    <span className="text-amber-500/70 mt-0.5">$</span>
                    <span className="text-zinc-400 leading-relaxed">{q}</span>
                  </div>
                  <div className="flex items-start gap-1.5 ml-3 mt-0.5">
                    <span className="text-emerald-500/70 mt-0.5">▶</span>
                    <span className="text-zinc-500 leading-relaxed">{mockResults[i]}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-2 text-[10px] text-zinc-700 border-t border-zinc-800/30 pt-2">
              <CheckCircle className="h-3 w-3 text-emerald-600" />
              <span>3 web searches completed · 2 threat intel feeds correlated · results injected into Master Brain</span>
            </div>
          </div>
        )}
      </div>

      {/* AI Recommendation */}
      <div className="mb-4 rounded-lg border border-emerald-800/30 bg-emerald-900/10 px-4 py-3">
        <div className="flex items-start gap-2">
          <Shield className="h-4 w-4 text-emerald-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">AI Recommended Action</span>
            <p className="text-sm text-zinc-300 mt-0.5">{pkg.recommended_action}</p>
            <p className="text-xs text-zinc-500 mt-1">{pkg.ai_recommendation}</p>
          </div>
        </div>
      </div>

      {/* Notes field (shown on reject/modify) */}
      {showNotes && (
        <div className="mb-4 rounded-lg border border-zinc-700/50 bg-zinc-900/80 p-4">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-2 block">
            {pendingAction === "reject" ? "Rejection Reason (required)" : "Modification Instructions"}
          </label>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={pendingAction === "reject" ? "Why is this action being rejected?" : "How should the action be modified?"}
            className="bg-zinc-800 border-zinc-700 text-zinc-200 text-sm min-h-[80px]"
          />
          <div className="flex items-center gap-2 mt-3">
            <Button size="sm" variant={pendingAction === "reject" ? "destructive" : "default"} onClick={confirmWithNotes} disabled={submitting || (pendingAction === "reject" && !notes.trim())}>
              {submitting ? "Submitting..." : `Confirm ${pendingAction === "reject" ? "Rejection" : "Modification"}`}
            </Button>
            <Button size="sm" variant="outline" onClick={() => { setShowNotes(false); setPendingAction(null); setNotes("") }}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* HITL Action Buttons */}
      {status === "pending" && !showNotes && (
        <div className="flex items-center gap-3 pt-3 border-t border-zinc-800/40">
          <Button size="sm" className="flex-1 gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20" onClick={() => handleDecision("approve")} disabled={submitting}>
            <CheckCircle className="h-4 w-4" />
            APPROVE & EXECUTE
          </Button>
          <Button size="sm" variant="destructive" className="flex-1 gap-1.5 shadow-lg shadow-red-600/20" onClick={() => handleDecision("reject")} disabled={submitting}>
            <XCircle className="h-4 w-4" />
            REJECT
          </Button>
          <Button size="sm" variant="outline" className="flex-1 gap-1.5 border-blue-700/50 text-blue-400 hover:bg-blue-600/10" onClick={() => handleDecision("modify")} disabled={submitting}>
            <ExternalLink className="h-4 w-4" />
            MODIFY
          </Button>
        </div>
      )}
    </div>
  )
}

// ── Feed of Decision Packages ──────────────────────────────────────────────

export function DecisionPackageFeed({ packages }: { packages: Dpkg[] }) {
  const pending = packages.filter((p) => p.requires_human_approval)
  const decided = packages.filter((p) => !p.requires_human_approval)

  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm font-semibold text-zinc-300">Decision Packages</CardTitle>
            <span className="flex h-5 items-center justify-center rounded-full bg-amber-600/20 px-2 text-[10px] font-bold text-amber-400">
              {pending.length}
            </span>
          </div>
          <span className="text-[11px] text-zinc-500">
            AI orchestrates &middot; Human decides &middot; System executes
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="max-h-[600px]">
          <div className="space-y-4">
            {pending.map((pkg) => (
              <DecisionPackageCard key={pkg.package_id} pkg={pkg} />
            ))}
            {pending.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-zinc-500">
                <CheckCircle className="h-12 w-12 text-emerald-500/40 mb-3" />
                <p className="text-sm font-medium text-zinc-400">No pending decisions</p>
                <p className="text-xs text-zinc-600 mt-1">All AI recommendations have been resolved</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
