"use client"

import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"
import { Gauge, BookOpen, Zap, Shield } from "lucide-react"

interface SystemStatus {
  status: string
  services: Record<string, { status: string; models?: number; knowledge_bases?: number; documents?: number; connected?: boolean }>
  orchestrator_running: boolean
  ws_clients: number
  hitl_pending: number
  gap_loop_pending: number
  audit_chain_length: number
  rl_accuracy: number
  version: string
  timestamp: string
}

const DEFAULT_SERVICES: SystemStatus["services"] = {
  ollama: { status: "unavailable" },
  redis: { status: "unavailable" },
  vector_store: { status: "unavailable" },
  n8n: { status: "unavailable" },
  wazuh: { status: "unavailable" },
}

function GaugeRing({
  value,
  max,
  label,
  sub,
  icon: Icon,
  color,
}: {
  value: number
  max: number
  label: string
  sub: string
  icon: React.ElementType
  color: string
}) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  const circumference = 2 * Math.PI * 28
  const offset = circumference - (pct / 100) * circumference

  return (
    <div className="flex items-center gap-3 min-w-0">
      <div className="relative flex-shrink-0 w-16 h-16">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="28" fill="none" stroke="rgb(39 39 42)" strokeWidth="4" />
          <circle
            cx="32"
            cy="32"
            r="28"
            fill="none"
            stroke={color}
            strokeWidth="4"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <Icon className={cn("h-5 w-5")} style={{ color }} />
        </div>
      </div>
      <div className="min-w-0">
        <p className="text-sm font-bold text-zinc-200 truncate">{label}</p>
        <p className="text-[10px] text-zinc-500 truncate">
          {value.toLocaleString()} / {max.toLocaleString()} &middot; {sub}
        </p>
      </div>
    </div>
  )
}

export function KpiBar() {
  const [status, setStatus] = useState<SystemStatus | null>(null)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("/api/system/status")
        if (res.ok) {
          setStatus(await res.json())
        }
      } catch {
        // backend not running
      }
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 10_000)
    return () => clearInterval(interval)
  }, [])

  const s = status ?? { services: DEFAULT_SERVICES, hitl_pending: 0, rl_accuracy: 0, ws_clients: 0, gap_loop_pending: 0, audit_chain_length: 0 }

  // Compute derived KPIs
  const hiveLoad = s.services.ollama.status === "ok"
    ? Math.min(50 + s.services.ollama.models! * 10 + s.ws_clients * 5, 100)
    : 0

  const ragSize = s.services.vector_store.status === "ok"
    ? s.services.vector_store.documents ?? 0
    : 0

  const soarActions = Math.max(0, s.gap_loop_pending + s.hitl_pending)

  const mitreCoverage = Math.round(s.rl_accuracy * 100)

  return (
    <div className="rounded-xl border border-zinc-800/50 bg-zinc-900/40 p-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <GaugeRing
          value={hiveLoad}
          max={100}
          label="AI Hive-Mind Load"
          sub={s.services.ollama.status === "ok" ? `${s.services.ollama.models} models` : "offline"}
          icon={Gauge}
          color="#fbbf24"
        />
        <GaugeRing
          value={ragSize}
          max={Math.max(ragSize, 200)}
          label="RAG Memory Size"
          sub={`${s.services.vector_store.status === "ok" ? s.services.vector_store.knowledge_bases ?? 0 : 0} KBs`}
          icon={BookOpen}
          color="#34d399"
        />
        <GaugeRing
          value={soarActions}
          max={Math.max(soarActions, 20)}
          label="SOAR Actions Today"
          sub={`${s.ws_clients} clients connected`}
          icon={Zap}
          color="#a78bfa"
        />
        <GaugeRing
          value={mitreCoverage}
          max={100}
          label="MITRE ATT&CK Coverage"
          sub={`${s.audit_chain_length} audit entries`}
          icon={Shield}
          color="#60a5fa"
        />
      </div>
    </div>
  )
}
