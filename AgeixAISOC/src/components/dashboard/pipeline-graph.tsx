"use client"

import { useMemo } from "react"

export interface PipelineEvent {
  stage: "ingestion" | "hive" | "rag" | "hitl" | "soar"
  status: "idle" | "active" | "done" | "error"
}

const STAGES = [
  { id: "ingestion", label: "Ingestion", sub: "Wazuh / UEBA", x: 0 },
  { id: "hive", label: "AgeixAI Hive-Mind", sub: "6 Agents", x: 1 },
  { id: "rag", label: "RAG Memory & OSINT", sub: "Deep Research", x: 2 },
  { id: "hitl", label: "HITL Decision", sub: "Human-in-the-Loop", x: 3 },
  { id: "soar", label: "SOAR Execution", sub: "n8n / FortiGate", x: 4 },
] as const

const STATUS_COLORS: Record<string, string> = {
  idle: "stroke-zinc-700",
  active: "stroke-amber-400",
  done: "stroke-emerald-400",
  error: "stroke-red-500",
}

const GLOW_FILTERS = {
  idle: "",
  active: "url(#glowAmber)",
  done: "url(#glowEmerald)",
  error: "url(#glowRed)",
}

function ArrowIcon({ active }: { active: boolean }) {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
      <path
        d="M5 12h14m-6-6 6 6-6 6"
        stroke={active ? "#fbbf24" : "#3f3f46"}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={active ? "animate-pulse" : ""}
      />
    </svg>
  )
}

export function PipelineGraph({ events }: { events: PipelineEvent[] }) {
  const stageStates = useMemo(() => {
    const map: Record<string, { status: string; count: number }> = {}
    for (const s of STAGES) map[s.id] = { status: "idle", count: 0 }
    for (const e of events) {
      if (map[e.stage]) {
        map[e.stage].status = e.status
        map[e.stage].count++
      }
    }
    return map
  }, [events])

  return (
    <div className="rounded-xl border border-zinc-800/50 bg-zinc-900/40 p-4 overflow-hidden">
      <svg style={{ position: "absolute", width: 0, height: 0 }}>
        <defs>
          <filter id="glowAmber">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feFlood floodColor="#fbbf24" floodOpacity="0.6" />
            <feComposite in2="blur" operator="in" />
            <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glowEmerald">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feFlood floodColor="#34d399" floodOpacity="0.6" />
            <feComposite in2="blur" operator="in" />
            <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glowRed">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feFlood floodColor="#ef4444" floodOpacity="0.6" />
            <feComposite in2="blur" operator="in" />
            <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
      </svg>

      <div className="flex items-center justify-between gap-1 min-w-[720px]">
        {STAGES.map((stage, i) => {
          const state = stageStates[stage.id]
          const isActive = state.status === "active"
          const isDone = state.status === "done"
          const isError = state.status === "error"
          const borderColor = isError
            ? "border-red-500/60"
            : isActive
              ? "border-amber-500/60"
              : isDone
                ? "border-emerald-500/60"
                : "border-zinc-700/50"
          const bgColor = isError
            ? "bg-red-500/10"
            : isActive
              ? "bg-amber-500/10"
              : isDone
                ? "bg-emerald-500/10"
                : "bg-zinc-800/30"
          const textColor = isError
            ? "text-red-400"
            : isActive
              ? "text-amber-300"
              : isDone
                ? "text-emerald-300"
                : "text-zinc-500"

          return (
            <div key={stage.id} className="flex items-center gap-1 flex-1">
              <div
                className={`relative flex flex-col items-center justify-center rounded-lg border px-3 py-2.5 transition-all duration-500 flex-1 ${borderColor} ${bgColor} ${
                  isActive ? "shadow-[0_0_12px_rgba(251,191,36,0.15)] scale-[1.02]" : ""
                }`}
              >
                {/* Pulse ring for active */}
                {isActive && (
                  <span className="absolute inset-0 rounded-lg animate-pulse ring-1 ring-amber-400/30" />
                )}

                <span className={`text-[11px] font-bold tracking-tight leading-tight ${textColor}`}>
                  {stage.label}
                </span>
                <span className="text-[9px] text-zinc-600 mt-0.5">{stage.sub}</span>

                {/* Event count badge */}
                {state.count > 0 && (
                  <span
                    className={`absolute -top-2 -right-2 flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-bold ${
                      isError ? "bg-red-600 text-white" : isActive ? "bg-amber-600 text-black" : "bg-zinc-700 text-zinc-300"
                    }`}
                  >
                    {state.count}
                  </span>
                )}
              </div>

              {/* Arrow to next stage */}
              {i < STAGES.length - 1 && (
                <div className="flex-shrink-0">
                  <ArrowIcon active={isActive || isDone} />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
