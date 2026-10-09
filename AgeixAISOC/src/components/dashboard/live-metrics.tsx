"use client"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { Clock, ShieldAlert, Activity, BrainCircuit, Gauge, Target } from "lucide-react"

type MetricCard = {
  label: string
  value: string | number
  unit?: string
  icon: typeof Clock
  trend: "up" | "down" | "neutral"
  trendValue: string
  color: "emerald" | "red" | "amber" | "blue" | "purple" | "cyan"
}

const metrics: MetricCard[] = [
  { label: "MTTD", value: 47, unit: "s", icon: Clock, trend: "down", trendValue: "-12%", color: "emerald" },
  { label: "MTTR", value: "2m 8s", icon: Clock, trend: "down", trendValue: "-8%", color: "emerald" },
  { label: "Active Incidents", value: 7, icon: ShieldAlert, trend: "up", trendValue: "+3", color: "red" },
  { label: "Pending Decisions", value: 12, icon: Activity, trend: "up", trendValue: "+5", color: "amber" },
  { label: "AI Accuracy", value: "93.7%", icon: BrainCircuit, trend: "up", trendValue: "+1.2%", color: "purple" },
  { label: "Coverage Score", value: 78, unit: "%", icon: Target, trend: "up", trendValue: "+4%", color: "cyan" },
]

const colorMap = {
  emerald: { bg: "bg-emerald-600/15", text: "text-emerald-400", icon: "text-emerald-500", border: "border-emerald-700/30" },
  red: { bg: "bg-red-600/15", text: "text-red-400", icon: "text-red-500", border: "border-red-700/30" },
  amber: { bg: "bg-amber-600/15", text: "text-amber-400", icon: "text-amber-500", border: "border-amber-700/30" },
  blue: { bg: "bg-blue-600/15", text: "text-blue-400", icon: "text-blue-500", border: "border-blue-700/30" },
  purple: { bg: "bg-purple-600/15", text: "text-purple-400", icon: "text-purple-500", border: "border-purple-700/30" },
  cyan: { bg: "bg-cyan-600/15", text: "text-cyan-400", icon: "text-cyan-500", border: "border-cyan-700/30" },
}

export function LiveMetrics() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {metrics.map((m) => {
        const c = colorMap[m.color]
        return (
          <Card key={m.label} className={cn("border-zinc-800/50 bg-zinc-900/40", c.border)}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{m.label}</span>
                <m.icon className={cn("h-4 w-4", c.icon)} />
              </div>
              <div className="flex items-baseline gap-1">
                <span className={cn("text-2xl font-bold tracking-tight", c.text)}>
                  {m.value}
                </span>
                {m.unit && <span className="text-sm text-zinc-500 font-medium">{m.unit}</span>}
              </div>
              <div className="mt-1 flex items-center gap-1">
                <span className={cn(
                  "text-[11px] font-medium",
                  m.trend === "up" && m.label === "Active Incidents" ? "text-red-400" :
                  m.trend === "down" && m.label !== "Active Incidents" ? "text-emerald-400" :
                  "text-zinc-500"
                )}>
                  {m.trendValue}
                </span>
                <span className="text-[10px] text-zinc-600">vs 24h</span>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
