"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { incidents } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { Shield, Gauge, Lightbulb, Search, Swords, Microscope, Clock, ChevronRight } from "lucide-react"
import type { Incident, IncidentEvent, AIAgent } from "@/lib/types"

const agentIcons: Record<AIAgent, typeof Shield> = {
  "Threat Detection": Shield,
  "Risk Scoring": Gauge,
  "Recommendation": Lightbulb,
  "Threat Hunter": Search,
  "Red Team": Swords,
  "Forensics": Microscope,
}

const agentColors: Record<AIAgent, string> = {
  "Threat Detection": "text-emerald-400 bg-emerald-600/15 border-emerald-700/30",
  "Risk Scoring": "text-amber-400 bg-amber-600/15 border-amber-700/30",
  "Recommendation": "text-blue-400 bg-blue-600/15 border-blue-700/30",
  "Threat Hunter": "text-purple-400 bg-purple-600/15 border-purple-700/30",
  "Red Team": "text-red-400 bg-red-600/15 border-red-700/30",
  "Forensics": "text-cyan-400 bg-cyan-600/15 border-cyan-700/30",
}

const severityConfig = {
  Critical: "border-red-700/40 bg-red-600/10",
  High: "border-red-700/25 bg-red-600/5",
  Medium: "border-amber-700/25 bg-amber-600/5",
  Low: "border-blue-700/25 bg-blue-600/5",
}

function IncidentCard({ incident }: { incident: Incident }) {
  return (
    <div className={cn("rounded-xl border p-5", severityConfig[incident.severity])}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-bold text-zinc-200">{incident.title}</span>
            <Badge variant={incident.severity === "Critical" ? "critical" : incident.severity === "High" ? "destructive" : incident.severity === "Medium" ? "warning" : "info"} className="text-[9px] px-1.5">
              {incident.severity}
            </Badge>
            <Badge variant={incident.status === "Active" ? "destructive" : incident.status === "Contained" ? "warning" : incident.status === "Investigating" ? "info" : "secondary"} className="text-[9px] px-1.5">
              {incident.status}
            </Badge>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-zinc-500">
            <span>{incident.id}</span>
            <span>&bull;</span>
            <span>{incident.mitreTactic}</span>
            <span>&bull;</span>
            <span>{incident.mitreTechnique.slice(0, 40)}</span>
          </div>
        </div>
        <div className="flex items-center gap-1 text-[11px] text-zinc-500">
          <Clock className="h-3 w-3" />
          {new Date(incident.startedAt).toLocaleTimeString()}
        </div>
      </div>

      {/* Affected Hosts */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {incident.affectedHosts.map((host) => (
          <Badge key={host} variant="outline" className="text-[10px] font-mono">
            {host}
          </Badge>
        ))}
      </div>

      {/* Timeline */}
      <div className="relative space-y-0">
        {incident.timeline.map((event, idx) => {
          const Icon = agentIcons[event.agent]
          return (
            <div key={idx} className="flex gap-3 pb-4 last:pb-0 relative">
              {/* Timeline line */}
              {idx < incident.timeline.length - 1 && (
                <div className="absolute left-[15px] top-8 bottom-0 w-px bg-zinc-800" />
              )}
              {/* Agent icon */}
              <div className={cn("flex h-8 w-8 items-center justify-center rounded-full border flex-shrink-0", agentColors[event.agent])}>
                <Icon className="h-3.5 w-3.5" />
              </div>
              {/* Event content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-zinc-300">{event.agent}</span>
                  <span className="text-[10px] text-zinc-600">{new Date(event.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-xs text-zinc-400 mt-0.5">{event.action}</p>
                <p className="text-[11px] text-zinc-500 mt-0.5">{event.detail}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function IncidentTimeline() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-zinc-300">Active Incidents</CardTitle>
          <Badge variant="destructive" className="text-[10px]">{incidents.filter((i) => i.status === "Active").length} Active</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[600px]">
          <div className="px-4 pb-4 space-y-4">
            {incidents.map((inc) => (
              <IncidentCard key={inc.id} incident={inc} />
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

// Fix the template literal issue above
