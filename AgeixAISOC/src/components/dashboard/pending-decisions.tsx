"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { pendingDecisions } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { Shield, AlertTriangle, CheckCircle, XCircle, Activity, ExternalLink, Clock, Target } from "lucide-react"
import type { PendingDecision, DecisionStatus } from "@/lib/types"

const severityConfig = {
  Critical: { badge: "critical", icon: AlertTriangle, border: "border-red-700/40", bg: "bg-red-600/5", glow: "shadow-red-600/10" },
  High: { badge: "destructive", icon: AlertTriangle, border: "border-red-700/25", bg: "bg-red-600/5", glow: "shadow-red-600/5" },
  Medium: { badge: "warning", icon: Activity, border: "border-amber-700/25", bg: "bg-amber-600/5", glow: "shadow-amber-600/5" },
  Low: { badge: "info", icon: Activity, border: "border-blue-700/25", bg: "bg-blue-600/5", glow: "shadow-blue-600/5" },
}

function DecisionCard({ decision }: { decision: PendingDecision }) {
  const [status, setStatus] = useState<DecisionStatus>(decision.status)
  const sev = severityConfig[decision.severity]

  return (
    <div
      className={cn(
        "relative rounded-xl border p-5 transition-all duration-300",
        sev.border,
        sev.bg,
        sev.glow,
        "hover:shadow-lg hover:border-zinc-600/50"
      )}
    >
      {/* Live indicator for pending */}
      {status === "Pending" && (
        <div className="absolute top-4 right-4 flex items-center gap-1.5">
          <span className="flex h-2 w-2">
            <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-amber-400 opacity-75" />
            <span className="inline-flex h-2 w-2 rounded-full bg-amber-500" />
          </span>
          <span className="text-[10px] font-medium text-amber-400 uppercase tracking-wider">Awaiting Decision</span>
        </div>
      )}

      {status !== "Pending" && (
        <div className="absolute top-4 right-4">
          {status === "Approved" && <span className="flex items-center gap-1 text-[11px] font-medium text-green-400"><CheckCircle className="h-3.5 w-3.5" /> Approved</span>}
          {status === "Rejected" && <span className="flex items-center gap-1 text-[11px] font-medium text-red-400"><XCircle className="h-3.5 w-3.5" /> Rejected</span>}
          {status === "Modified" && <span className="flex items-center gap-1 text-[11px] font-medium text-blue-400"><ExternalLink className="h-3.5 w-3.5" /> Modified</span>}
        </div>
      )}

      {/* Header */}
      <div className="flex items-start gap-3 mb-3 pr-32">
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg border", sev.border, "bg-zinc-900/80")}>
          <sev.icon className={cn("h-4 w-4", sev.badge === "critical" || sev.badge === "destructive" ? "text-red-400" : sev.badge === "warning" ? "text-amber-400" : "text-blue-400")} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="text-sm font-semibold text-zinc-200 truncate">{decision.title}</h3>
            <Badge variant={sev.badge as any} className="text-[10px] px-1.5 py-0">{decision.severity}</Badge>
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">{decision.source}</Badge>
          </div>
          <p className="text-xs text-zinc-400 line-clamp-2">{decision.description}</p>
        </div>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Risk Score</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <div className={cn(
              "h-2 w-16 rounded-full overflow-hidden bg-zinc-800",
            )}>
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  decision.riskScore >= 80 ? "bg-red-500" : decision.riskScore >= 60 ? "bg-amber-500" : "bg-blue-500"
                )}
                style={{ width: `${decision.riskScore}%` }}
              />
            </div>
            <span className={cn(
              "text-xs font-bold",
              decision.riskScore >= 80 ? "text-red-400" : decision.riskScore >= 60 ? "text-amber-400" : "text-blue-400"
            )}>{decision.riskScore}/100</span>
          </div>
        </div>
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">MITRE</span>
          <p className="text-xs font-medium text-zinc-300 truncate mt-0.5">{decision.mitreTactic}</p>
        </div>
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Target</span>
          <p className="text-xs font-medium text-zinc-300 mt-0.5">{decision.affectedHost}</p>
        </div>
        <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Time</span>
          <p className="text-xs font-medium text-zinc-300 mt-0.5">{new Date(decision.timestamp).toLocaleTimeString()}</p>
        </div>
      </div>

      {/* Recommended Action */}
      <div className="mb-4 rounded-lg border border-emerald-800/30 bg-emerald-900/10 px-4 py-3">
        <div className="flex items-start gap-2">
          <Shield className="h-4 w-4 text-emerald-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">AI Recommended Action</span>
            <p className="text-sm text-zinc-300 mt-0.5">{decision.recommendedAction}</p>
          </div>
        </div>
      </div>

      {/* Action Buttons (only when pending) */}
      {status === "Pending" && (
        <div className="flex items-center gap-3 pt-2 border-t border-zinc-800/40">
          <Button
            size="sm"
            variant="success"
            className="flex-1 gap-1.5"
            onClick={() => setStatus("Approved")}
          >
            <CheckCircle className="h-4 w-4" />
            APPROVE
          </Button>
          <Button
            size="sm"
            variant="destructive"
            className="flex-1 gap-1.5"
            onClick={() => setStatus("Rejected")}
          >
            <XCircle className="h-4 w-4" />
            REJECT
          </Button>
          <Button
            size="sm"
            variant="default"
            className="flex-1 gap-1.5 bg-blue-600 hover:bg-blue-500 shadow-blue-600/20"
            onClick={() => setStatus("Modified")}
          >
            <ExternalLink className="h-4 w-4" />
            MODIFY
          </Button>
        </div>
      )}
    </div>
  )
}

export function PendingDecisionsFeed() {
  const pending = pendingDecisions.filter((d) => d.status === "Pending")
  const decided = pendingDecisions.filter((d) => d.status !== "Pending")

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm font-semibold text-zinc-300">Pending Human Decisions</CardTitle>
            <span className="flex h-5 items-center justify-center rounded-full bg-amber-600/20 px-2 text-[10px] font-bold text-amber-400">
              {pending.length}
            </span>
          </div>
          <CardDescription className="text-[11px]">
            AI recommends &middot; Human decides &middot; System executes
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {pending.map((d) => (
            <DecisionCard key={d.id} decision={d} />
          ))}
          {pending.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-zinc-500">
              <CheckCircle className="h-12 w-12 text-emerald-500/40 mb-3" />
              <p className="text-sm font-medium text-zinc-400">No pending decisions</p>
              <p className="text-xs text-zinc-600 mt-1">All AI recommendations have been resolved</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
