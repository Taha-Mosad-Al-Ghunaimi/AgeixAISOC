"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { incidents } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { Cpu, Globe, FileText, Database, HardDrive, Microscope } from "lucide-react"
import type { ForensicArtifact } from "@/lib/types"

const typeIcons = {
  Process: Cpu,
  Network: Globe,
  File: FileText,
  Registry: Database,
  Memory: HardDrive,
  Disk: HardDrive,
}

const typeColors: Record<string, string> = {
  Process: "border-blue-700/30 bg-blue-600/10 text-blue-400",
  Network: "border-emerald-700/30 bg-emerald-600/10 text-emerald-400",
  File: "border-amber-700/30 bg-amber-600/10 text-amber-400",
  Registry: "border-purple-700/30 bg-purple-600/10 text-purple-400",
  Memory: "border-red-700/30 bg-red-600/10 text-red-400",
  Disk: "border-cyan-700/30 bg-cyan-600/10 text-cyan-400",
}

export function ForensicArtifacts() {
  const allArtifacts = incidents.flatMap((i) => i.forensicArtifacts)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-zinc-300">Forensic Artifacts Collected</CardTitle>
          <Badge variant="info" className="text-[10px]">{allArtifacts.length} artifacts</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[600px]">
          <div className="px-4 pb-4 space-y-2">
            {allArtifacts.map((art) => {
              const Icon = typeIcons[art.type]
              return (
                <div
                  key={art.id}
                  className={cn("flex items-start gap-3 rounded-lg border p-3", typeColors[art.type])}
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900/60 flex-shrink-0">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-zinc-200">{art.name}</span>
                      <Badge variant="outline" className="text-[9px] px-1">{art.type}</Badge>
                      <Badge variant="secondary" className="text-[9px] px-1">{art.collectedBy}</Badge>
                    </div>
                    {art.path && <p className="text-[11px] text-zinc-500 font-mono mt-0.5 truncate">{art.path}</p>}
                    <p className="text-[11px] text-zinc-400 mt-0.5">{art.relevance}</p>
                    {art.hash && <p className="text-[10px] text-zinc-600 font-mono mt-0.5">SHA256: {art.hash}</p>}
                  </div>
                  <span className="text-[10px] text-zinc-600 flex-shrink-0">
                    {new Date(art.collectedAt).toLocaleTimeString()}
                  </span>
                </div>
              )
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
