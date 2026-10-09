"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { agentStatuses } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import {
  Activity,
  Shield,
  Gauge,
  Lightbulb,
  Search,
  Swords,
  Microscope,
  ArrowRight,
  CheckCircle2,
  Loader2,
} from "lucide-react"

const agentIcons = {
  "Threat Detection": Shield,
  "Risk Scoring": Gauge,
  "Recommendation": Lightbulb,
  "Threat Hunter": Search,
  "Red Team": Swords,
  "Forensics": Microscope,
}

const agentColors: Record<string, string> = {
  "Threat Detection": "border-emerald-700/40 bg-emerald-600/10",
  "Risk Scoring": "border-amber-700/40 bg-amber-600/10",
  "Recommendation": "border-blue-700/40 bg-blue-600/10",
  "Threat Hunter": "border-purple-700/40 bg-purple-600/10",
  "Red Team": "border-red-700/40 bg-red-600/10",
  "Forensics": "border-cyan-700/40 bg-cyan-600/10",
}

const agentTextColors: Record<string, string> = {
  "Threat Detection": "text-emerald-400",
  "Risk Scoring": "text-amber-400",
  "Recommendation": "text-blue-400",
  "Threat Hunter": "text-purple-400",
  "Red Team": "text-red-400",
  "Forensics": "text-cyan-400",
}

const connections = [
  { from: "Threat Detection", to: "Risk Scoring" },
  { from: "Risk Scoring", to: "Recommendation" },
  { from: "Recommendation", to: null },
  { from: "Threat Hunter", to: "Threat Detection" },
  { from: "Red Team", to: "Threat Detection" },
  { from: "Red Team", to: "Threat Hunter" },
  { from: "Forensics", to: "Threat Detection" },
  { from: "Forensics", to: "Risk Scoring" },
  { from: "Red Team", to: "Forensics" },
]

export function AgentGraph() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-zinc-300">AI Agent Communication Graph</CardTitle>
          <Badge variant="default" className="text-[10px] gap-1">
            <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            6/6 Online
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative">
          {/* Agent Nodes */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
            {agentStatuses.map((a) => {
              const Icon = agentIcons[a.agent]
              const isRedTeam = a.agent === "Red Team"
              return (
                <div
                  key={a.agent}
                  className={cn(
                    "relative rounded-xl border p-4 transition-all duration-300 hover:scale-[1.02]",
                    agentColors[a.agent],
                    a.status === "Error" && "border-red-600/50 bg-red-600/10"
                  )}
                >
                  {/* Agent Type Indicator */}
                  <div className="flex items-center gap-2 mb-2">
                    <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", isRedTeam ? "bg-red-600/20" : "bg-zinc-900/60")}>
                      <Icon className={cn("h-4 w-4", agentTextColors[a.agent])} />
                    </div>
                    <div>
                      <span className={cn("text-sm font-bold", agentTextColors[a.agent])}>{a.agent}</span>
                      {isRedTeam && <Badge variant="destructive" className="ml-2 text-[8px] px-1 py-0">Offensive</Badge>}
                    </div>
                  </div>

                  {/* Status & Task */}
                  <div className="flex items-center gap-2 mb-1.5">
                    {a.status === "Active" && <Activity className="h-3 w-3 text-emerald-400 animate-pulse" />}
                    {a.status === "Analyzing" && <Loader2 className="h-3 w-3 text-amber-400 animate-spin" />}
                    {a.status === "Idle" && <CheckCircle2 className="h-3 w-3 text-zinc-600" />}
                    {a.status === "Error" && <Activity className="h-3 w-3 text-red-400 animate-pulse" />}
                    <span className={cn(
                      "text-[10px] font-medium uppercase tracking-wider",
                      a.status === "Active" ? "text-emerald-400" :
                      a.status === "Analyzing" ? "text-amber-400" :
                      a.status === "Idle" ? "text-zinc-500" :
                      "text-red-400"
                    )}>{a.status}</span>
                  </div>
                  <p className="text-[11px] text-zinc-500 truncate">{a.currentTask}</p>

                  {/* Stats */}
                  <div className="mt-3 flex items-center justify-between text-[10px] text-zinc-600 border-t border-zinc-800/40 pt-2">
                    <span>{a.tasksCompleted.toLocaleString()} tasks</span>
                    <span className={cn("font-medium", a.accuracy >= 95 ? "text-emerald-400" : a.accuracy >= 85 ? "text-amber-400" : "text-zinc-400")}>
                      {a.accuracy}% acc
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Connection Flow Legend */}
          <div className="rounded-lg border border-zinc-800/40 bg-zinc-900/40 p-3">
            <div className="flex items-center flex-wrap gap-x-6 gap-y-2 text-[11px] text-zinc-500">
              <span className="font-medium text-zinc-400">Data Flow:</span>
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Alert Ingest
              </span>
              <span className="flex items-center gap-1">
                <ArrowRight className="h-3 w-3 text-amber-500" /> Risk Scoring
              </span>
              <span className="flex items-center gap-1">
                <ArrowRight className="h-3 w-3 text-blue-500" /> Recommendation
              </span>
              <span className="flex items-center gap-1">
                <ArrowRight className="h-3 w-3 text-red-500" /> Red Team Loop
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
