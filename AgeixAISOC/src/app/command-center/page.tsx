"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { LiveMetrics } from "@/components/dashboard/live-metrics"
import { MitreHeatmap } from "@/components/dashboard/mitre-heatmap"
import { DecisionPackageFeed } from "@/components/dashboard/decision-package-card"
import { RecentAlerts } from "@/components/dashboard/recent-alerts"
import { SystemStatus } from "@/components/dashboard/system-status"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Wifi, WifiOff, Send } from "lucide-react"
import { cn } from "@/lib/utils"
import { useWp4WebSocket } from "@/hooks/use-wp4-websocket"
import { sendAlert, type DecisionPackage } from "@/lib/api"
import { HiddenConnectionsBanner } from "@/components/dashboard/hidden-connections-banner"
import { QuickSearch } from "@/components/dashboard/quick-search"
import { ExternalWebhookMonitor } from "@/components/dashboard/external-webhook-monitor"
import { PipelineGraph, type PipelineEvent } from "@/components/dashboard/pipeline-graph"
import { UnifiedLiveFeed, type FeedEntry } from "@/components/dashboard/unified-live-feed"
import { KpiBar } from "@/components/dashboard/kpi-bar"
import { HitlKanban, type KanbanCard, type KanbanStatus } from "@/components/dashboard/hitl-kanban"

// ── Simulate Attack Button ─────────────────────────────────────────────────

function SimulateAttackButton({ onAlertSent }: { onAlertSent: () => void }) {
  const [sending, setSending] = useState(false)

  const handleSimulate = useCallback(async () => {
    setSending(true)
    try {
      await sendAlert({
        rule_id: Math.floor(100000 + Math.random() * 900000),
        src_ip: `${Math.floor(Math.random() * 223) + 1}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
        dst_ip: "10.0.40.10",
        severity: ["critical", "high", "medium", "low"][Math.floor(Math.random() * 4)] as any,
        description: "Simulated attack alert from WP1",
        agent_name: "SRV-WEB-01",
        raw_event: {},
      })
      onAlertSent()
    } catch { /* toast */ } finally {
      setSending(false)
    }
  }, [onAlertSent])

  return (
    <Button size="sm" variant="outline" className="gap-1.5 border-emerald-700/50 text-emerald-400 hover:bg-emerald-600/10" onClick={handleSimulate} disabled={sending}>
      <Send className="h-3.5 w-3.5" />
      {sending ? "Sending..." : "Simulate WP1 Alert"}
    </Button>
  )
}

// ── SOC Analyst View (Unified Mission Control) ────────────────────────────

export default function CommandCenterPage() {
  const { isConnected, decisionPackages, systemLogs } = useWp4WebSocket()
  const [mockDecisions, setMockDecisions] = useState<DecisionPackage[]>([])

  // Parse WS decision packages into typed objects
  useEffect(() => {
    const fresh = decisionPackages
      .filter((msg) => msg.data)
      .map((msg) => msg.data as unknown as DecisionPackage)
      .filter((dp) => !mockDecisions.find((m) => m.package_id === dp.package_id))
    if (fresh.length > 0) {
      setMockDecisions((prev) => [...fresh, ...prev].slice(0, 20))
    }
  }, [decisionPackages])

  const handleAlertSent = useCallback(() => {
    // WS will receive the ai_decision automatically
  }, [])

  // ── Derive Pipeline Events from WS data ─────────────────────────────────

  const pipelineEvents: PipelineEvent[] = useMemo(() => {
    const events: PipelineEvent[] = []
    for (const dp of decisionPackages) {
      if (dp.type === "ai_decision" || dp.data?.package_id) {
        events.push({ stage: "ingestion", status: "done" })
        events.push({ stage: "hive", status: "done" })
        events.push({ stage: "rag", status: "done" })
        events.push({
          stage: "hitl",
          status: (dp.data as any)?.requires_human_approval ? "active" : "done",
        })
        events.push({ stage: "soar", status: "idle" })
      }
    }
    // If a decision was just made, mark SOAR as done
    for (const log of systemLogs) {
      if (log.message?.toLowerCase().includes("executed") || log.message?.toLowerCase().includes("soar")) {
        events.push({ stage: "soar", status: "done" })
      }
    }
    return events.slice(-10)
  }, [decisionPackages, systemLogs])

  // ── Derive Unified Feed entries from WS logs ────────────────────────────

  const feedEntries: FeedEntry[] = useMemo(() => {
    const entries: FeedEntry[] = []
    for (const log of systemLogs) {
      const msg = (log.message || "").toLowerCase()
      const ts = log.timestamp || new Date().toISOString()
      if (msg.includes("ueba") || msg.includes("anomaly")) {
        entries.push({ source: "ueba", message: log.message || "", timestamp: ts })
      } else if (msg.includes("osint") || msg.includes("dark") || msg.includes("tor")) {
        entries.push({ source: "osint", message: log.message || "", timestamp: ts })
      } else if (msg.includes("agent") || msg.includes("brain") || msg.includes("reason") || msg.includes("analyz")) {
        entries.push({ source: "agent", message: log.message || "", timestamp: ts })
      } else if (msg.includes("soar") || msg.includes("execut") || msg.includes("forti") || msg.includes("block")) {
        entries.push({ source: "soar", message: log.message || "", timestamp: ts })
      }
    }
    return entries.slice(-100)
  }, [systemLogs])

  // ── Derive Kanban Cards from decision packages ──────────────────────────

  const kanbanCards: KanbanCard[] = useMemo(() => {
    const cards: KanbanCard[] = []
    for (const msg of decisionPackages) {
      const dp = msg.data as unknown as DecisionPackage
      if (!dp?.package_id) continue

      const status: KanbanStatus = dp.requires_human_approval ? "awaiting_human" : "executed"
      cards.push({
        id: dp.package_id,
        title: dp.alert.description || `Alert Rule ${dp.alert.rule_id}`,
        description: dp.ai_recommendation || dp.recommended_action || "No recommendation",
        status,
        risk_score: dp.risk_score,
        source: dp.alert.agent_name || "wazuh",
        timestamp: dp.created_at || new Date().toISOString(),
      })
    }
    return cards.slice(0, 30)
  }, [decisionPackages])

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Unified Mission Control</h1>
          <p className="text-sm text-zinc-500 mt-1">
            AgeixAI orchestrates &middot; AgeixAI detects &middot; AgeixAI recommends &middot; <span className="text-emerald-400 font-medium">HUMAN DECIDES</span> &middot; System executes
          </p>
        </div>
        <div className="flex items-center gap-3">
          <SimulateAttackButton onAlertSent={handleAlertSent} />
          <Badge variant="default" className={cn("gap-1.5 px-3 py-1.5 text-xs", isConnected ? "border-emerald-700/30" : "border-red-700/30")}>
            {isConnected ? (
              <>
                <span className="flex h-2 w-2">
                  <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </span>
                <Wifi className="h-3 w-3 text-emerald-400" />
                WS Connected
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 text-red-400" />
                WS Disconnected
              </>
            )}
          </Badge>
        </div>
      </div>

      <Separator className="bg-zinc-800/60" />

      {/* 1. Master KPI Dashboard (Top Bar) */}
      <KpiBar />

      {/* 2. Unified Pipeline Graph */}
      <PipelineGraph events={pipelineEvents} />

      {/* Hidden Connections — Cross-Agent Correlation Alerts */}
      <HiddenConnectionsBanner />

      {/* AgeixAI Quick Search */}
      <QuickSearch />

      {/* System Status (4 Work Packages) */}
      <SystemStatus />

      {/* Live Metrics */}
      <LiveMetrics />

      {/* 3. Main Content Grid — Decision Packages + Multi-Source Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 space-y-6">
          <DecisionPackageFeed packages={mockDecisions} />
        </div>
        <div className="lg:col-span-2 space-y-6">
          <UnifiedLiveFeed entries={feedEntries} />
          <ExternalWebhookMonitor />
          <MitreHeatmap />
          <RecentAlerts />
        </div>
      </div>

      {/* 4. Interactive HITL Kanban (Bottom) */}
      <HitlKanban cards={kanbanCards} />
    </div>
  )
}
