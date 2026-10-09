"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { pendingDecisions } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { AlertTriangle, Info } from "lucide-react"
import type { PendingDecision } from "@/lib/types"

export function RecentAlerts() {
  const [alerts, setAlerts] = useState<PendingDecision[]>(pendingDecisions)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-zinc-300">Recent Alerts</CardTitle>
          <Badge variant="secondary" className="text-[10px]">Live</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[420px]">
          <div className="px-4 pb-4 space-y-1">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-start gap-3 rounded-lg px-3 py-2.5 hover:bg-zinc-800/40 transition-colors cursor-pointer group"
              >
                <div className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full mt-0.5",
                  alert.severity === "Critical" || alert.severity === "High" ? "bg-red-600/15 text-red-400" :
                  alert.severity === "Medium" ? "bg-amber-600/15 text-amber-400" :
                  "bg-blue-600/15 text-blue-400"
                )}>
                  {alert.severity === "Critical" || alert.severity === "High" ?
                    <AlertTriangle className="h-3.5 w-3.5" /> :
                    <Info className="h-3.5 w-3.5" />
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-zinc-300 truncate group-hover:text-zinc-100 transition-colors">
                      {alert.title}
                    </span>
                    <Badge variant={alert.severity === "Critical" ? "critical" : alert.severity === "High" ? "destructive" : alert.severity === "Medium" ? "warning" : "info"} className="text-[9px] px-1 py-0 flex-shrink-0">
                      {alert.severity}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] text-zinc-500">{alert.source}</span>
                    <span className="text-zinc-700">&bull;</span>
                    <span className="text-[11px] text-zinc-600">{alert.mitreTactic}</span>
                    <span className="text-zinc-700">&bull;</span>
                    <span className="text-[11px] text-zinc-600">{alert.affectedHost}</span>
                  </div>
                </div>
                <span className="text-[10px] text-zinc-600 flex-shrink-0 mt-1">
                  {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
