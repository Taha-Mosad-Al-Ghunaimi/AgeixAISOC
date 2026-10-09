"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { getBrainStats, type HiveMindAgentActivity } from "@/lib/api"
import { Swords, Search, Shield, Gauge, Lightbulb, Microscope, BrainCircuit, Activity } from "lucide-react"

const AGENTS = [
  { id: "red_team", label: "Red Team", icon: Swords, color: "#ef4444", glow: "rgba(239,68,68,0.3)" },
  { id: "blue_team", label: "Blue Team", icon: Search, color: "#22c55e", glow: "rgba(34,197,94,0.3)" },
  { id: "threat_detection", label: "Threat Detection", icon: Shield, color: "#34d399", glow: "rgba(52,211,153,0.3)" },
  { id: "risk_scoring", label: "Risk Scoring", icon: Gauge, color: "#f59e0b", glow: "rgba(245,158,11,0.3)" },
  { id: "recommendation", label: "Recommendation", icon: Lightbulb, color: "#3b82f6", glow: "rgba(59,130,246,0.3)" },
  { id: "threat_hunter", label: "Threat Hunter", icon: Search, color: "#a855f7", glow: "rgba(168,85,247,0.3)" },
  { id: "forensics", label: "Forensics", icon: Microscope, color: "#06b6d4", glow: "rgba(6,182,212,0.3)" },
]

const CENTER_RADIUS = 48
const ORBIT_RADIUS = 170
const NODE_RADIUS = 38
const ARENA_SIZE = 520
const CENTER = ARENA_SIZE / 2
const AGENT_COUNT = AGENTS.length

function getAgentPosition(index: number) {
  const angle = (index / AGENT_COUNT) * Math.PI * 2 - Math.PI / 2
  return {
    x: CENTER + ORBIT_RADIUS * Math.cos(angle),
    y: CENTER + ORBIT_RADIUS * Math.sin(angle),
  }
}

const CONTRIBUTION_LABELS: Record<string, string[]> = {
  red_team: ["Ports: 22,80,443,445", "CVE-2025-44228 found", "Exploit: SESSION_OPENED"],
  blue_team: ["Wazuh alert 87104", "LSASS access detected", "Remediation: isolate host"],
  threat_detection: ["Triage: true_positive", "MITRE T1003.001", "Priority: 85/100"],
  risk_scoring: ["Score: 95", "Blast radius: 12", "Financial: $2.3M"],
  recommendation: ["Playbook: PB-001", "ISO A.16.1.5", "NIST RS.CO"],
  threat_hunter: ["Sigma: 3 matches", "IEX download detected", "Beaconing: every 60s"],
  forensics: ["Timeline: +3 artifacts", "Prefetch: powershell.exe", "Event 4663: lsass"],
}

function getContributionLines(agentId: string): string[] {
  const labels = CONTRIBUTION_LABELS[agentId] || []
  const shuffled = [...labels].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, 2)
}

export function HiveMindGraph() {
  const [activity, setActivity] = useState<Record<string, HiveMindAgentActivity>>({})
  const [activeFlow, setActiveFlow] = useState<string | null>(null)
  const [hoveredAgent, setHoveredAgent] = useState<string | null>(null)
  const [contributions, setContributions] = useState<Record<string, string[]>>({})
  const [cycleNum, setCycleNum] = useState(0)
  const flowInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await getBrainStats()
        setActivity(res.data.hive_mind_activity)
        setCycleNum(res.data.current_cycle)
      } catch { /* offline */ }
    }
    fetchStats()
    const interval = setInterval(fetchStats, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const ids = Object.keys(CONTRIBUTION_LABELS)
    const shuffled = [...ids].sort(() => Math.random() - 0.5)
    let idx = 0

    const setNext = () => {
      const agent = shuffled[idx % shuffled.length]
      setActiveFlow(agent)
      setContributions((prev) => ({ ...prev, [agent]: getContributionLines(agent) }))
      idx++
    }

    setNext()
    flowInterval.current = setInterval(setNext, 3500)
    return () => { if (flowInterval.current) clearInterval(flowInterval.current) }
  }, [])

  const agentActivity = (agentId: string) => {
    const a = activity[agentId]
    if (!a) return { status: "inactive" as const, action: "", idle_seconds: 0 }
    return a
  }

  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm font-semibold text-zinc-300">Hive-Mind Swarm</CardTitle>
            <Badge variant="default" className="text-[10px] gap-1 px-2 py-0.5">
              <span className="flex h-1.5 w-1.5"><span className="absolute inline-flex h-1.5 w-1.5 animate-ping rounded-full bg-emerald-400 opacity-75" /><span className="inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" /></span>
              Cycle #{cycleNum}
            </Badge>
          </div>
          <Badge variant="outline" className="text-[10px] text-zinc-500">
            Swarm Active
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex justify-center">
          <svg width={ARENA_SIZE} height={ARENA_SIZE} className="overflow-visible">
            <defs>
              <radialGradient id="center-glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="rgba(52,211,153,0.4)" />
                <stop offset="60%" stopColor="rgba(52,211,153,0.1)" />
                <stop offset="100%" stopColor="rgba(52,211,153,0)" />
              </radialGradient>
              {AGENTS.map((a) => (
                <radialGradient key={a.id} id={`glow-${a.id}`} cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor={a.glow} />
                  <stop offset="100%" stopColor="rgba(0,0,0,0)" />
                </radialGradient>
              ))}
              <filter id="pulse">
                <feDropShadow dx={0} dy={0} stdDeviation={8} floodColor="#34d399" floodOpacity={0.5} />
              </filter>
            </defs>

            {/* Orbit ring */}
            <circle cx={CENTER} cy={CENTER} r={ORBIT_RADIUS + NODE_RADIUS + 12}
              fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth={1} strokeDasharray="4 6" />

            {/* Connection lines with data flow */}
            {AGENTS.map((a, idx) => {
              const pos = getAgentPosition(idx)
              const isActive = activeFlow === a.id
              const isHovered = hoveredAgent === a.id
              const act = agentActivity(a.id)
              return (
                <g key={a.id}>
                  {/* Static connection line */}
                  <line x1={CENTER} y1={CENTER} x2={pos.x} y2={pos.y}
                    stroke={isActive || isHovered ? a.color : "rgba(255,255,255,0.08)"}
                    strokeWidth={isActive ? 2 : isHovered ? 1.5 : 1}
                    opacity={isActive ? 0.8 : 0.4}
                  />
                  {/* Animated data dot */}
                  {isActive && (
                    <circle r={4} fill={a.color} filter="url(#pulse)">
                      <animateMotion dur="1.2s" repeatCount="indefinite"
                        path={`M${CENTER},${CENTER} L${pos.x},${pos.y}`} />
                    </circle>
                  )}
                  {isActive && (
                    <circle r={4} fill={a.color} filter="url(#pulse)">
                      <animateMotion dur="1.2s" repeatCount="indefinite"
                        path={`M${pos.x},${pos.y} L${CENTER},${CENTER}`} begin="0.6s" />
                    </circle>
                  )}
                </g>
              )
            })}

            {/* Agent contribution bubbles */}
            {AGENTS.map((a, idx) => {
              const pos = getAgentPosition(idx)
              const lines = contributions[a.id] || []
              const isActive = activeFlow === a.id
              const act = agentActivity(a.id)
              const isOnline = act.status === "active"

              return (
                <g key={`bubble-${a.id}`}>
                  {/* Contribution text bubbles on active flow */}
                  {isActive && lines.map((line, li) => {
                    const bubbleX = pos.x > CENTER ? pos.x + NODE_RADIUS + 10 : pos.x - NODE_RADIUS - 10
                    const bubbleY = pos.y + li * 18 - (lines.length - 1) * 9
                    const anchor = pos.x > CENTER ? "start" : "end"
                    return (
                      <g key={li}>
                        <rect x={anchor === "start" ? bubbleX - 4 : bubbleX - 120}
                          y={bubbleY - 8} width={124} height={16} rx={4}
                          fill="rgba(0,0,0,0.7)" stroke={a.color} strokeWidth={0.5} strokeOpacity={0.4} />
                        <text x={anchor === "start" ? bubbleX : bubbleX - 116}
                          y={bubbleY + 4} fill={a.color} fontSize={9}
                          fontFamily="monospace" textAnchor={anchor}>
                          {line}
                        </text>
                      </g>
                    )
                  })}
                </g>
              )
            })}

            {/* Agent nodes */}
            {AGENTS.map((a, idx) => {
              const pos = getAgentPosition(idx)
              const act = agentActivity(a.id)
              const isOnline = act.status === "active"
              const isHovered = hoveredAgent === a.id
              const isFlowing = activeFlow === a.id

              return (
                <g key={`node-${a.id}`}
                  onMouseEnter={() => setHoveredAgent(a.id)}
                  onMouseLeave={() => setHoveredAgent(null)}
                  style={{ cursor: "pointer" }}>
                  {/* Glow ring */}
                  {(isOnline || isFlowing) && (
                    <circle cx={pos.x} cy={pos.y} r={NODE_RADIUS + 8} fill="none"
                      stroke={a.color} strokeWidth={1.5} opacity={0.3}>
                      {isFlowing && <animate attributeName="r" values={`${NODE_RADIUS + 4};${NODE_RADIUS + 14};${NODE_RADIUS + 4}`} dur="2s" repeatCount="indefinite" />}
                      {isFlowing && <animate attributeName="opacity" values="0.4;0.1;0.4" dur="2s" repeatCount="indefinite" />}
                    </circle>
                  )}
                  {/* Node background */}
                  <circle cx={pos.x} cy={pos.y} r={NODE_RADIUS}
                    fill={isOnline ? `${a.color}15` : "rgba(255,255,255,0.03)"}
                    stroke={isFlowing ? a.color : isOnline ? `${a.color}60` : "rgba(255,255,255,0.1)"}
                    strokeWidth={isFlowing ? 2.5 : 1.5}
                  />
                  {/* Status dot */}
                  <circle cx={pos.x + 22} cy={pos.y - 22} r={4}
                    fill={isOnline ? "#22c55e" : "#52525b"}>
                    {isOnline && <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />}
                  </circle>
                  {/* Agent icon */}
                  <a.icon x={pos.x - 10} y={pos.y - 10} width={20} height={20}
                    color={isOnline ? a.color : "#52525b"} />
                  {/* Agent label */}
                  <text x={pos.x} y={pos.y + NODE_RADIUS + 16}
                    textAnchor="middle" fill={isOnline ? "#e4e4e7" : "#52525b"}
                    fontSize={10} fontFamily="sans-serif" fontWeight={600}>
                    {a.label}
                  </text>
                  {/* Tooltip on hover */}
                  {isHovered && (
                    <g>
                      <rect x={pos.x - NODE_RADIUS - 40} y={pos.y + NODE_RADIUS + 22}
                        width={160} height={38} rx={4}
                        fill="rgba(9,9,11,0.95)" stroke="rgba(255,255,255,0.1)" strokeWidth={0.5} />
                      <text x={pos.x} y={pos.y + NODE_RADIUS + 36}
                        textAnchor="middle" fill="#a1a1aa" fontSize={9}>
                        {act.action || "idle"}
                      </text>
                      <text x={pos.x} y={pos.y + NODE_RADIUS + 50}
                        textAnchor="middle" fill="#52525b" fontSize={8}>
                        idle {Math.round(act.idle_seconds)}s
                      </text>
                    </g>
                  )}
                </g>
              )
            })}

            {/* Center: Master Brain */}
            <g>
              <circle cx={CENTER} cy={CENTER} r={CENTER_RADIUS + 18}
                fill="url(#center-glow)" />
              {[1, 2, 3].map((i) => (
                <circle key={i} cx={CENTER} cy={CENTER} r={CENTER_RADIUS + i * 5}
                  fill="none" stroke="rgba(52,211,153,0.15)" strokeWidth={1}>
                  <animate attributeName="r" values={`${CENTER_RADIUS + i * 5};${CENTER_RADIUS + i * 5 + 8};${CENTER_RADIUS + i * 5}`}
                    dur={`${1.5 + i * 0.3}s`} repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.3;0.05;0.3"
                    dur={`${1.5 + i * 0.3}s`} repeatCount="indefinite" />
                </circle>
              ))}
              <circle cx={CENTER} cy={CENTER} r={CENTER_RADIUS}
                fill="rgba(52,211,153,0.12)"
                stroke="#34d399" strokeWidth={2.5} filter="url(#pulse)" />
              <BrainCircuit x={CENTER - 18} y={CENTER - 18} width={36} height={36}
                color="#34d399" />
              <text x={CENTER} y={CENTER + 30}
                textAnchor="middle" fill="#34d399" fontSize={10}
                fontFamily="sans-serif" fontWeight={700} letterSpacing={1}>
                MASTER BRAIN
              </text>
              <text x={CENTER} y={CENTER + 42}
                textAnchor="middle" fill="#6ee7b7" fontSize={8}
                fontFamily="monospace" opacity={0.7}>
                AgeixAI Core
              </text>
            </g>
          </svg>
        </div>

        {/* Legend */}
        <div className="mt-2 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-[10px] text-zinc-600">
          <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Active</span>
          <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-zinc-500" /> Idle</span>
          <span className="flex items-center gap-1"><Activity className="h-3 w-3 text-emerald-400" /> Data Flow</span>
          <span className="flex items-center gap-1"><BrainCircuit className="h-3 w-3 text-emerald-500" /> Orchestrator</span>
        </div>
      </CardContent>
    </Card>
  )
}
