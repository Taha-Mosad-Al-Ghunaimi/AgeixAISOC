"use client"

import { HiveMindGraph } from "@/components/ai-brain/hive-mind-graph"
import { RAGMemoryPanel } from "@/components/ai-brain/rag-memory-panel"
import { MemoryTimeline } from "@/components/ai-brain/memory-timeline"
import { BrainStatsKpi } from "@/components/ai-brain/brain-stats-kpi"
import { DetectionGapLoop } from "@/components/ai-brain/detection-gap-loop"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { BrainCircuit } from "lucide-react"

export default function AiBrainPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <BrainCircuit className="h-6 w-6 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100">The Master Brain</h1>
          </div>
          <p className="text-sm text-zinc-500 mt-1">
            Hive-Mind shared state &middot; Adaptive RAG learning &middot; Self-healing detection gaps
          </p>
        </div>
        <Badge variant="default" className="gap-1.5 px-3 py-1.5 text-xs">
          <span className="flex h-2 w-2">
            <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          Hive Online
        </Badge>
      </div>

      <Separator className="bg-zinc-800/60" />

      {/* Brain Stats KPIs */}
      <BrainStatsKpi />

      {/* Main Grid: Hive-Mind Graph + RAG Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <HiveMindGraph />
        </div>
        <div className="lg:col-span-1">
          <RAGMemoryPanel />
        </div>
      </div>

      {/* Bottom Row: Memory Timeline + Detection Gap Loop */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MemoryTimeline />
        <DetectionGapLoop />
      </div>
    </div>
  )
}
