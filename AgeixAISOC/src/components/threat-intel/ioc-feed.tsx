"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { iocs } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { Globe, AlertTriangle, RefreshCw, Filter, Hash, Link, Mail, Server } from "lucide-react"
import type { IOC } from "@/lib/types"

const typeIcons = { IP: Server, Domain: Globe, URL: Link, Hash: Hash, Email: Mail }

const typeColors: Record<string, string> = {
  IP: "border-emerald-700/30 text-emerald-400",
  Domain: "border-blue-700/30 text-blue-400",
  URL: "border-purple-700/30 text-purple-400",
  Hash: "border-amber-700/30 text-amber-400",
  Email: "border-cyan-700/30 text-cyan-400",
}

const sourceColors: Record<string, string> = {
  VirusTotal: "border-transparent bg-emerald-600/20 text-emerald-400",
  AbuseIPDB: "border-transparent bg-red-600/20 text-red-400",
  "AlienVault OTX": "border-transparent bg-blue-600/20 text-blue-400",
  MISP: "border-transparent bg-purple-600/20 text-purple-400",
  ThreatFox: "border-transparent bg-amber-600/20 text-amber-400",
}

export function IOCFeed() {
  const [filterType, setFilterType] = useState<string>("all")

  const filtered = filterType === "all" ? iocs : iocs.filter((ioc) => ioc.type === filterType)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-zinc-300">Threat Intelligence Feed</CardTitle>
            <CardDescription className="text-[11px] mt-0.5">{iocs.length} IoCs &middot; Updated every 15 min</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="h-8 w-32 text-[11px]">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="IP">IP</SelectItem>
                <SelectItem value="Domain">Domain</SelectItem>
                <SelectItem value="URL">URL</SelectItem>
                <SelectItem value="Hash">Hash</SelectItem>
                <SelectItem value="Email">Email</SelectItem>
              </SelectContent>
            </Select>
            <Button size="sm" variant="outline" className="h-8 gap-1 text-[11px]">
              <RefreshCw className="h-3 w-3" />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[600px]">
          <div className="px-4 pb-4 space-y-2">
            {filtered.map((ioc) => {
              const Icon = typeIcons[ioc.type]
              return (
                <div
                  key={ioc.id}
                  className={cn(
                    "flex items-start gap-3 rounded-lg border p-3 transition-all hover:bg-zinc-800/30",
                    typeColors[ioc.type].split(" ")[0],
                    "border-zinc-800/40"
                  )}
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900/60 flex-shrink-0">
                    <Icon className={cn("h-4 w-4", typeColors[ioc.type].split(" ")[1])} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono font-medium text-zinc-200 truncate max-w-[280px]">{ioc.value}</span>
                      <Badge variant={ioc.severity === "Critical" ? "critical" : ioc.severity === "High" ? "destructive" : ioc.severity === "Medium" ? "warning" : "info"} className="text-[9px] px-1 flex-shrink-0">
                        {ioc.severity}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary" className={cn("text-[9px] px-1", sourceColors[ioc.source])}>
                        {ioc.source}
                      </Badge>
                      <span className="text-[10px] text-zinc-600">Confidence: {ioc.confidence}%</span>
                      <span className="text-zinc-700">&bull;</span>
                      <span className="text-[10px] text-zinc-600">{ioc.type}</span>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {ioc.tags.map((tag) => (
                        <span key={tag} className="text-[9px] px-1.5 py-0.5 rounded-full bg-zinc-800/60 text-zinc-500 border border-zinc-700/40">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
