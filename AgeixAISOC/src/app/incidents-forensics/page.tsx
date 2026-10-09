"use client"

import { IncidentTimeline } from "@/components/incidents/incident-timeline"
import { ForensicArtifacts } from "@/components/incidents/forensic-artifacts"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Search } from "lucide-react"

export default function IncidentsForensicsPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Search className="h-6 w-6 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Incidents & Forensics</h1>
          </div>
          <p className="text-sm text-zinc-500 mt-1">
            Automated incident timelines &middot; AI-collected forensic artifacts from disk, memory, and network
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="destructive" className="gap-1.5 px-3 py-1.5 text-xs">
            3 Active Incidents
          </Badge>
        </div>
      </div>

      <Separator className="bg-zinc-800/60" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <IncidentTimeline />
        <ForensicArtifacts />
      </div>
    </div>
  )
}
