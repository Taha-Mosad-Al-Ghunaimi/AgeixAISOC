"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Globe, LayoutDashboard, Brain } from "lucide-react"
import { cn } from "@/lib/utils"
import { getHealth } from "@/lib/api"

interface WPStatus {
  id: string
  name: string
  abbrev: string
  description: string
  icon: typeof Activity
  online: boolean
}

const defaultStatus: WPStatus[] = [
  { id: "wp1", name: "WP1 — SIEM & EDR", abbrev: "SIEM", description: "Wazuh, Zeek, EDR agents", icon: Activity, online: true },
  { id: "wp2", name: "WP2 — Threat Intel & API", abbrev: "TI/API", description: "FortiGate, VirusTotal, MISP", icon: Globe, online: true },
  { id: "wp3", name: "WP3 — Dashboard & HITL", abbrev: "Dashboard", description: "Command center, audit trail", icon: LayoutDashboard, online: true },
  { id: "wp4", name: "WP4 — AgeixAI Brain", abbrev: "Brain", description: "6 agents, 9 MCP, RL engine", icon: Brain, online: true },
]

export function SystemStatus() {
  const [workPackages, setWorkPackages] = useState(defaultStatus)
  const [lastCheck, setLastCheck] = useState<string>("")

  useEffect(() => {
    async function checkHealth() {
      try {
        const health = await getHealth()
        setWorkPackages((prev) =>
          prev.map((wp) => ({
            ...wp,
            online: health.status === "healthy",
          }))
        )
        setLastCheck(new Date().toLocaleTimeString())
      } catch {
        setWorkPackages((prev) =>
          prev.map((wp) => ({
            ...wp,
            online: wp.id === "wp3", // Dashboard is always "online" (it's us)
          }))
        )
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm font-semibold text-zinc-300">Work Package Status</CardTitle>
            <Badge variant="default" className="text-[10px] px-1.5 py-0 gap-1">
              <span className="flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-1.5 w-1.5 animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </span>
              All Online
            </Badge>
          </div>
          {lastCheck && (
            <span className="text-[10px] text-zinc-600 font-mono">Last check: {lastCheck}</span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {workPackages.map((wp) => {
            const Icon = wp.icon
            return (
              <div
                key={wp.id}
                className={cn(
                  "relative rounded-lg border p-3 transition-all",
                  wp.online
                    ? "border-emerald-800/30 bg-emerald-900/5"
                    : "border-red-800/30 bg-red-900/5"
                )}
              >
                <div className="flex items-center gap-2 mb-2">
                  <div className={cn(
                    "flex h-2 w-2",
                  )}>
                    <span className={cn(
                      "absolute inline-flex h-2 w-2 animate-ping rounded-full opacity-75",
                      wp.online ? "bg-emerald-400" : "bg-red-400"
                    )} />
                    <span className={cn(
                      "inline-flex h-2 w-2 rounded-full",
                      wp.online ? "bg-emerald-500" : "bg-red-500"
                    )} />
                  </div>
                  <span className={cn(
                    "text-[10px] font-bold uppercase tracking-wider",
                    wp.online ? "text-emerald-400" : "text-red-400"
                  )}>
                    {wp.online ? "Online" : "Offline"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Icon className={cn("h-4 w-4", wp.online ? "text-emerald-500" : "text-red-500")} />
                  <div>
                    <p className="text-xs font-semibold text-zinc-200">{wp.abbrev}</p>
                    <p className="text-[10px] text-zinc-500">{wp.description}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
