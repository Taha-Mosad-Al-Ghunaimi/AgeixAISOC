"use client"

import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

interface Props {
  active: boolean
  onComplete?: () => void
}

const AGENTS = [
  { id: "clear_web", label: "Clear Web", x: 18, y: 18, color: "emerald" },
  { id: "social_media", label: "Social Media", x: 82, y: 18, color: "cyan" },
  { id: "dark_web", label: "Dark Web", x: 18, y: 82, color: "violet" },
  { id: "reasoning", label: "Reasoning", x: 82, y: 82, color: "amber" },
]

export function OsintSwarmAnimation({ active, onComplete }: Props) {
  const [phase, setPhase] = useState<"idle" | "activating" | "streaming" | "complete">("idle")
  const [nodes, setNodes] = useState<Record<string, number>>({})

  useEffect(() => {
    if (!active) {
      setPhase("idle")
      return
    }
    setPhase("activating")
    const t1 = setTimeout(() => setPhase("streaming"), 800)
    const t2 = setTimeout(() => {
      setPhase("complete")
      onComplete?.()
    }, 4000)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [active, onComplete])

  useEffect(() => {
    if (phase !== "streaming") return
    const interval = setInterval(() => {
      setNodes({
        clear_web: Math.random(),
        social_media: Math.random(),
        dark_web: Math.random(),
        reasoning: Math.random(),
      })
    }, 300)
    return () => clearInterval(interval)
  }, [phase])

  if (!active) return null

  return (
    <div className="relative w-full h-64 bg-zinc-900/60 rounded-xl border border-zinc-800/50 overflow-hidden">
      {/* Grid background */}
      <svg className="absolute inset-0 w-full h-full opacity-10" viewBox="0 0 100 100">
        <defs>
          <pattern id="grid-sm" width="4" height="4" patternUnits="userSpaceOnUse">
            <path d="M 4 0 L 0 0 0 4" fill="none" stroke="currentColor" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100" height="100" fill="url(#grid-sm)" />
      </svg>

      {/* Center: Master Brain */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
        <div className={cn(
          "flex h-16 w-16 items-center justify-center rounded-full transition-all duration-500",
          phase === "streaming" ? "bg-gradient-to-br from-emerald-500 to-cyan-600 shadow-lg shadow-emerald-500/30 scale-110" : "bg-zinc-800 shadow-md",
        )}>
          <svg className="h-8 w-8 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2a10 10 0 1 0 10 10h-2a8 8 0 1 1-8-8V2z" />
            <path d="M12 2v4a6 6 0 1 1-6 6H2c0 5.523 4.477 10 10 10s10-4.477 10-10S17.523 2 12 2z" />
          </svg>
        </div>
        {phase === "streaming" && (
          <div className="absolute inset-0 h-16 w-16 rounded-full animate-ping bg-emerald-400/20" />
        )}
        <span className="block text-center text-[10px] font-semibold text-zinc-400 mt-2 tracking-wider uppercase">
          Master Brain
        </span>
      </div>

      {/* Agent Nodes */}
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
        {AGENTS.map((agent) => (
          <g key={agent.id}>
            {/* Data stream lines to center */}
            {phase === "streaming" && (
              <line
                x1={agent.x} y1={agent.y} x2={50} y2={50}
                stroke={agent.color === "emerald" ? "#10b981" : agent.color === "cyan" ? "#06b6d4" : agent.color === "violet" ? "#8b5cf6" : "#f59e0b"}
                strokeWidth="0.5"
                className="animate-pulse"
                strokeDasharray="2 2"
                opacity={0.4 + (nodes[agent.id] ?? 0) * 0.4}
              />
            )}
          </g>
        ))}
      </svg>

      {AGENTS.map((agent) => {
        const pulsing = phase === "streaming"
        return (
          <div
            key={agent.id}
            className="absolute z-20 flex flex-col items-center"
            style={{ left: `${agent.x - 7}%`, top: `${agent.y - 7}%` }}
          >
            <div className={cn(
              "flex h-14 w-14 items-center justify-center rounded-full border-2 transition-all duration-500",
              agent.color === "emerald" ? "border-emerald-500 bg-emerald-600/10" :
              agent.color === "cyan" ? "border-cyan-500 bg-cyan-600/10" :
              agent.color === "violet" ? "border-violet-500 bg-violet-600/10" :
              "border-amber-500 bg-amber-600/10",
              pulsing && `animate-pulse shadow-lg shadow-${agent.color}-500/20 scale-110`,
              phase === "activating" && "animate-bounce",
            )}>
              <span className={cn(
                "text-xs font-bold",
                agent.color === "emerald" ? "text-emerald-400" :
                agent.color === "cyan" ? "text-cyan-400" :
                agent.color === "violet" ? "text-violet-400" :
                "text-amber-400",
              )}>{agent.label.charAt(0)}</span>
            </div>
            <span className="text-[10px] font-medium text-zinc-500 mt-1.5">{agent.label}</span>
          </div>
        )
      })}

      {phase === "streaming" && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-2">
          {["clear_web", "social_media", "dark_web", "reasoning"].map((a) => (
            <span key={a} className={cn(
              "h-1.5 w-1.5 rounded-full",
              a === "clear_web" ? "bg-emerald-500" : a === "social_media" ? "bg-cyan-500" : a === "dark_web" ? "bg-violet-500" : "bg-amber-500",
              "animate-pulse",
            )} />
          ))}
          <span className="text-[10px] text-zinc-600 ml-1">Swarm analyzing ...</span>
        </div>
      )}

      {phase === "complete" && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2">
          <span className="text-[10px] font-semibold text-emerald-400">Swarm Complete</span>
        </div>
      )}
    </div>
  )
}
