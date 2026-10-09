"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { getBrainStats, type AccuracyTrend } from "@/lib/api"
import { Database, BrainCircuit, TrendingUp, TrendingDown, Minus, BookOpen, Lightbulb, AlertCircle } from "lucide-react"

interface RAGMemoryPanelProps {
  className?: string
}

export function RAGMemoryPanel({ className }: RAGMemoryPanelProps) {
  const [ragSize, setRagSize] = useState<number | null>(null)
  const [accuracyTrend, setAccuracyTrend] = useState<AccuracyTrend | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getBrainStats()
        setRagSize(res.data.rag_memory_size)
        setAccuracyTrend(res.data.ai_accuracy_trend)
      } catch { /* offline */ }
      setLoading(false)
    }
    fetchData()
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [])

  const trendIcon = accuracyTrend?.trend === "improving" ? TrendingUp :
    accuracyTrend?.trend === "declining" ? TrendingDown : Minus
  const trendColor = accuracyTrend?.trend === "improving" ? "text-emerald-400" :
    accuracyTrend?.trend === "declining" ? "text-red-400" : "text-zinc-400"

  const mockRecentDecisions = [
    { id: "DP-A3B2C1", verdict: "approved", by: "soc-analyst-01", ago: "2 min ago", context: "Block C2 IP 185.130.5.23" },
    { id: "DP-F7E8D9", verdict: "rejected", by: "soc-analyst-03", ago: "15 min ago", context: "Isolate finance workstation" },
    { id: "DP-B4C5D6", verdict: "modified", by: "soc-analyst-01", ago: "1h ago", context: "Remediate SMB vulnerability" },
  ]

  return (
    <Card className={cn("border-zinc-800/50 bg-zinc-900/40", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-emerald-400" />
            <CardTitle className="text-sm font-semibold text-zinc-300">Adaptive Learning (RAG)</CardTitle>
          </div>
          <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-700/40">
            <span className="flex h-1.5 w-1.5 mr-1"><span className="absolute inline-flex h-1.5 w-1.5 animate-ping rounded-full bg-emerald-400 opacity-75" /><span className="inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" /></span>
            Learning
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Incidents Learned Counter */}
        <div className="rounded-xl border border-emerald-800/20 bg-emerald-900/10 p-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-1">
            <BookOpen className="h-4 w-4 text-emerald-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">Incidents Learned</span>
          </div>
          <div className="text-4xl font-bold tracking-tight text-emerald-300 font-mono">
            {loading ? "..." : (ragSize ?? 0).toLocaleString()}
          </div>
          <p className="text-[10px] text-zinc-600 mt-1">decisions embedded in vector memory</p>
        </div>

        {/* AI vs Human Alignment */}
        <div className="rounded-lg border border-zinc-800/40 bg-zinc-900/60 p-3">
          <div className="flex items-center gap-2 mb-3">
            <BrainCircuit className="h-3.5 w-3.5 text-purple-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
              AI vs Human Alignment
            </span>
            {accuracyTrend && (
              <Badge variant="outline" className={cn("text-[9px] ml-auto px-1.5", trendColor)}>
                {trendIcon({ className: "h-3 w-3 mr-0.5 inline" })}
                {accuracyTrend.trend}
              </Badge>
            )}
          </div>

          {/* Accuracy bar */}
          {accuracyTrend && (
            <div className="mb-3">
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="text-zinc-500">Accuracy</span>
                <span className={cn("font-bold font-mono", accuracyTrend.accuracy_pct >= 80 ? "text-emerald-400" : "text-amber-400")}>
                  {accuracyTrend.accuracy_pct}%
                </span>
              </div>
              <div className="h-2 w-full rounded-full overflow-hidden bg-zinc-800">
                <div
                  className={cn("h-full rounded-full transition-all duration-500", accuracyTrend.accuracy_pct >= 80 ? "bg-emerald-500" : "bg-amber-500")}
                  style={{ width: `${accuracyTrend.accuracy_pct}%` }}
                />
              </div>
              <div className="flex justify-between text-[9px] text-zinc-600 mt-1">
                <span>{accuracyTrend.matches} matches</span>
                <span>{accuracyTrend.mismatches} mismatches</span>
              </div>
            </div>
          )}

          {/* Context badges */}
          <div className="space-y-2">
            <div className="rounded-lg border border-emerald-800/20 bg-emerald-900/10 p-2.5">
              <div className="flex items-start gap-2">
                <Lightbulb className="h-3.5 w-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-[11px] text-emerald-300 font-medium">Based on 3 past similar incidents</p>
                  <p className="text-[10px] text-zinc-500 mt-0.5">100% human approval rate for C2 IP blocks</p>
                </div>
              </div>
            </div>
            <div className="rounded-lg border border-amber-800/20 bg-amber-900/10 p-2.5">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-3.5 w-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-[11px] text-amber-300 font-medium">Novel threat — no past memory</p>
                  <p className="text-[10px] text-zinc-500 mt-0.5">First sighting of this attack pattern</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recent RAG-learned decisions */}
        <div>
          <span className="text-[9px] font-semibold uppercase tracking-wider text-zinc-500 mb-2 block">
            Recently Learned
          </span>
          <div className="space-y-1.5">
            {mockRecentDecisions.map((d) => (
              <div key={d.id} className="flex items-center justify-between rounded-md bg-zinc-900/40 px-2.5 py-1.5 border border-zinc-800/30">
                <div className="flex items-center gap-2 min-w-0">
                  <span className={cn(
                    "text-[9px] font-mono font-bold px-1 py-0.5 rounded",
                    d.verdict === "approved" ? "text-emerald-400 bg-emerald-600/10" :
                    d.verdict === "rejected" ? "text-red-400 bg-red-600/10" :
                    "text-blue-400 bg-blue-600/10"
                  )}>
                    {d.verdict === "approved" ? "✓" : d.verdict === "rejected" ? "✗" : "~"}
                  </span>
                  <span className="text-[10px] text-zinc-400 truncate">{d.context}</span>
                </div>
                <span className="text-[9px] text-zinc-600 flex-shrink-0">{d.ago}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
