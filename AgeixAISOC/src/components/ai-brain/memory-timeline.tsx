"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { Clock, CheckCircle, XCircle, Edit3, BrainCircuit, ArrowRight, Database, Shield } from "lucide-react"

const LEARNING_EVENTS = [
  {
    time: "10:30 AM", label: "Human rejected AI recommendation to block IP X",
    detail: "AI updated memory to avoid blocking similar internal scans",
    type: "rejected" as const,
  },
  {
    time: "10:15 AM", label: "Human approved AI recommendation to block C2 IP 185.130.5.23",
    detail: "RAG stored: C2 IP block → 100% approval rate → reinforcement",
    type: "approved" as const,
  },
  {
    time: "9:52 AM", label: "Human modified AI remediation plan",
    detail: "Changed isolation scope from 'entire VLAN' to 'single host'. AI learned precision.",
    type: "modified" as const,
  },
  {
    time: "9:30 AM", label: "Master Brain queried RAG memory",
    detail: "3 similar past incidents found for T1071.001 C2 beaconing",
    type: "system" as const,
  },
  {
    time: "8:45 AM", label: "Human approved Sigma rule deployment",
    detail: "New Sigma rule for T1110.001 (SSH Brute Force) deployed to Wazuh. Coverage +5%",
    type: "approved" as const,
  },
  {
    time: "8:20 AM", label: "Gap loop identified missing coverage",
    detail: "Kerberoasting (T1558.003) not detected. AI generating Sigma rule.",
    type: "system" as const,
  },
  {
    time: "7:50 AM", label: "Human rejected host isolation recommendation",
    detail: "False positive — internal scanning tool detected. AI updated weight for similar events.",
    type: "rejected" as const,
  },
  {
    time: "7:15 AM", label: "RL weight adjustment: T1003.001 +3.2",
    detail: "Approved LSASS detection rule → increased confidence weight for credential dumping.",
    type: "approved" as const,
  },
]

const typeStyles = {
  approved: { dot: "bg-emerald-500", line: "bg-emerald-800/30", border: "border-emerald-800/20 bg-emerald-900/10", icon: CheckCircle, iconColor: "text-emerald-400" },
  rejected: { dot: "bg-red-500", line: "bg-red-800/30", border: "border-red-800/20 bg-red-900/10", icon: XCircle, iconColor: "text-red-400" },
  modified: { dot: "bg-blue-500", line: "bg-blue-800/30", border: "border-blue-800/20 bg-blue-900/10", icon: Edit3, iconColor: "text-blue-400" },
  system: { dot: "bg-purple-500", line: "bg-purple-800/30", border: "border-purple-800/20 bg-purple-900/10", icon: BrainCircuit, iconColor: "text-purple-400" },
}

export function MemoryTimeline() {
  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-cyan-400" />
            <CardTitle className="text-sm font-semibold text-zinc-300">Memory Timeline</CardTitle>
          </div>
          <Badge variant="outline" className="text-[10px] text-cyan-400 border-cyan-700/40">Real-Time</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="max-h-[360px] pr-2">
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-[9px] top-2 bottom-2 w-px bg-zinc-800/60" />

            <div className="space-y-0">
              {LEARNING_EVENTS.map((event, idx) => {
                const style = typeStyles[event.type]
                const Icon = style.icon
                const isFirst = idx === 0

                return (
                  <div key={idx} className="relative flex gap-4 pb-5 last:pb-0">
                    {/* Timeline dot */}
                    <div className="relative flex flex-col items-center">
                      <div className={cn("relative z-10 flex h-[18px] w-[18px] items-center justify-center rounded-full border-2 border-zinc-900", style.dot)} />
                      {/* Animated ring on latest */}
                      {isFirst && (
                        <span className="absolute inset-0 flex h-[18px] w-[18px] items-center justify-center">
                          <span className="absolute h-[18px] w-[18px] animate-ping rounded-full bg-emerald-400 opacity-30" />
                        </span>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[10px] font-mono font-bold text-zinc-500">{event.time}</span>
                        <Badge variant="outline" className={cn("text-[8px] px-1 py-0 uppercase", style.iconColor)}>
                          {event.type}
                        </Badge>
                      </div>
                      <div className={cn("rounded-lg border p-2.5", style.border)}>
                        <div className="flex items-start gap-2">
                          <Icon className={cn("h-3.5 w-3.5 mt-0.5 flex-shrink-0", style.iconColor)} />
                          <div>
                            <p className="text-[11px] font-medium text-zinc-300 leading-snug">{event.label}</p>
                            <p className="text-[10px] text-zinc-500 mt-0.5 leading-snug">{event.detail}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
