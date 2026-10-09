"use client"

import { useMemo, useState } from "react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Clock, UserCheck, CheckCircle2, AlertTriangle, Shield, Server, Globe, Brain } from "lucide-react"

export type KanbanStatus = "pending_analysis" | "awaiting_human" | "executed"

export interface KanbanCard {
  id: string
  title: string
  description: string
  status: KanbanStatus
  risk_score: number
  source: string
  timestamp: string
}

interface HitlKanbanProps {
  cards: KanbanCard[]
}

const COLUMNS: { id: KanbanStatus; label: string; icon: React.ElementType; color: string }[] = [
  { id: "pending_analysis", label: "Pending AI Analysis", icon: Clock, color: "text-amber-400" },
  { id: "awaiting_human", label: "Awaiting Human Decision", icon: UserCheck, color: "text-blue-400" },
  { id: "executed", label: "Executed", icon: CheckCircle2, color: "text-emerald-400" },
]

const SOURCE_ICONS: Record<string, React.ElementType> = {
  wazuh: Shield,
  ueba: Brain,
  external: Globe,
  default: Server,
}

function RiskBadge({ score }: { score: number }) {
  const color =
    score >= 80 ? "bg-red-500/20 text-red-400 border-red-500/30" :
    score >= 50 ? "bg-amber-500/20 text-amber-400 border-amber-500/30" :
    "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
  return (
    <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded border", color)}>
      {score}
    </span>
  )
}

function KanbanCardView({ card }: { card: KanbanCard }) {
  const SourceIcon = SOURCE_ICONS[card.source] ?? SOURCE_ICONS.default

  return (
    <div className="rounded-lg border border-zinc-700/50 bg-zinc-800/40 p-3 space-y-2 transition-all hover:border-zinc-600/50">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <SourceIcon className="h-3.5 w-3.5 text-zinc-500 flex-shrink-0" />
          <span className="text-xs font-semibold text-zinc-200 truncate">{card.title}</span>
        </div>
        <RiskBadge score={card.risk_score} />
      </div>

      <p className="text-[11px] text-zinc-500 line-clamp-2">{card.description}</p>

      <div className="flex items-center justify-between text-[9px] text-zinc-600">
        <span className="uppercase tracking-wider">{card.source}</span>
        <span>{new Date(card.timestamp).toLocaleTimeString("en-US", { hour12: false })}</span>
      </div>
    </div>
  )
}

export function HitlKanban({ cards }: HitlKanbanProps) {
  const grouped = useMemo(() => {
    const map: Record<KanbanStatus, KanbanCard[]> = {
      pending_analysis: [],
      awaiting_human: [],
      executed: [],
    }
    for (const c of cards) {
      if (map[c.status]) map[c.status].push(c)
    }
    return map
  }, [cards])

  return (
    <div className="rounded-xl border border-zinc-800/50 bg-zinc-900/40 p-4">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="h-4 w-4 text-amber-400" />
        <span className="text-sm font-semibold text-zinc-300">HITL Kanban — Human-in-the-Loop Decision Board</span>
        <span className="text-[10px] text-zinc-600 font-mono">{cards.length} total</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {COLUMNS.map((col) => {
          const colCards = grouped[col.id]
          return (
            <div
              key={col.id}
              className="rounded-lg border border-zinc-800/50 bg-zinc-900/60 p-3"
            >
              {/* Column header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-1.5">
                  <col.icon className={cn("h-4 w-4", col.color)} />
                  <span className={cn("text-xs font-bold", col.color)}>{col.label}</span>
                </div>
                <span className="text-[10px] text-zinc-600 font-mono bg-zinc-800/50 px-1.5 py-0.5 rounded">
                  {colCards.length}
                </span>
              </div>

              {/* Cards */}
              <ScrollArea className="h-[280px]">
                <div className="space-y-2 pr-1">
                  {colCards.length === 0 && (
                    <p className="text-[11px] text-zinc-700 text-center py-8 italic">
                      {col.id === "pending_analysis"
                        ? "No alerts in queue"
                        : col.id === "awaiting_human"
                          ? "All decisions resolved"
                          : "No executions yet"}
                    </p>
                  )}
                  {colCards.map((card) => (
                    <KanbanCardView key={card.id} card={card} />
                  ))}
                </div>
              </ScrollArea>
            </div>
          )
        })}
      </div>
    </div>
  )
}
