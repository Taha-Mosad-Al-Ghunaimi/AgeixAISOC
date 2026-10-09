"use client"

import { useState, useEffect, useCallback } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { X, Link2, AlertTriangle, Skull, Shield, Swords, Search, Microscope, Gauge, Lightbulb } from "lucide-react"
import { getBrainStats, type HiveMindAgentActivity } from "@/lib/api"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface Correlation {
  correlation_id: string
  rule_id: string
  title: string
  narrative: string
  severity: string
  agents_involved: string[]
  techniques: string[]
  recommendation: string
  timestamp: string
  resolved: boolean
}

const AGENT_ICONS: Record<string, typeof Shield> = {
  red_team: Swords,
  blue_team: Search,
  threat_detection: Shield,
  risk_scoring: Gauge,
  recommendation: Lightbulb,
  threat_hunter: Search,
  forensics: Microscope,
}

const SEVERITY_STYLES = {
  critical: { bg: "bg-red-600/10 border-red-700/30", text: "text-red-400", icon: Skull, badge: "destructive" as const },
  high: { bg: "bg-red-600/5 border-red-700/20", text: "text-red-400", icon: AlertTriangle, badge: "destructive" as const },
  medium: { bg: "bg-amber-600/5 border-amber-700/20", text: "text-amber-400", icon: AlertTriangle, badge: "warning" as const },
  low: { bg: "bg-blue-600/5 border-blue-700/20", text: "text-blue-400", icon: Link2, badge: "info" as const },
}

export function HiddenConnectionsBanner() {
  const [correlations, setCorrelations] = useState<Correlation[]>([])
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  const fetchCorrelations = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/correlations`)
      const json = await res.json()
      if (json.status === "success") {
        setCorrelations(json.data || [])
      }
    } catch { /* offline */ }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchCorrelations()
    const interval = setInterval(fetchCorrelations, 10000)
    return () => clearInterval(interval)
  }, [fetchCorrelations])

  const dismissCorrelation = (corrId: string) => {
    setDismissed((prev) => new Set([...prev, corrId]))
    fetch(`${API_BASE}/api/correlations/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ correlation_id: corrId }),
    }).catch(() => {})
  }

  const visible = correlations.filter((c) => !dismissed.has(c.correlation_id))

  if (visible.length === 0) return null

  const top = visible[0]
  const style = SEVERITY_STYLES[top.severity as keyof typeof SEVERITY_STYLES] || SEVERITY_STYLES.medium
  const Icon = style.icon
  const AgentIcon = AGENT_ICONS[top.agents_involved[0]] || Shield

  return (
    <div className={cn(
      "relative rounded-xl border p-4 transition-all duration-500",
      style.bg, style.text,
    )}>
      {/* Count badge */}
      {visible.length > 1 && (
        <Badge variant={style.badge} className="absolute -top-2 -right-2 text-[9px] px-1.5 py-0 z-10">
          +{visible.length - 1} more
        </Badge>
      )}

      <div className="flex items-start gap-3">
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg border", style.bg)}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5">
              <Link2 className="h-3.5 w-3.5" />
              Master Brain Link
            </span>
            <Badge variant={style.badge} className="text-[9px] px-1.5 py-0">{top.severity}</Badge>
          </div>

          <p className="text-sm font-semibold text-zinc-200 mb-1">{top.title}</p>
          <p className="text-xs text-zinc-400 leading-relaxed mb-2">{top.narrative}</p>

          {/* Agent badges */}
          <div className="flex flex-wrap items-center gap-2 mb-3">
            {top.agents_involved.map((agent) => {
              const AIcon = AGENT_ICONS[agent] || Shield
              return (
                <Badge key={agent} variant="outline" className="text-[9px] gap-1 px-2 py-0.5 text-zinc-400 border-zinc-700/50">
                  <AIcon className="h-3 w-3" />
                  {agent.replace("_", " ")}
                </Badge>
              )
            })}
            {top.techniques.length > 0 && (
              <span className="text-[9px] text-zinc-600 font-mono">
                {top.techniques.join(" · ")}
              </span>
            )}
          </div>

          {/* Recommendation + Dismiss */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
              <Shield className="h-3.5 w-3.5" />
              {top.recommendation}
            </span>
            <Button
              size="sm"
              variant="ghost"
              className="ml-auto h-7 text-[10px] text-zinc-500 hover:text-zinc-300 gap-1"
              onClick={() => dismissCorrelation(top.correlation_id)}
            >
              <X className="h-3 w-3" />
              Dismiss
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
