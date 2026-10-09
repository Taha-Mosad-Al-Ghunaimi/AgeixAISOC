"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { detectionGaps } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { Swords, Search, FileText, ShieldCheck, CheckCircle2, XCircle, ArrowRight, Loader2 } from "lucide-react"

const phases = [
  { key: "attack", label: "Red Team Attacks", icon: Swords, color: "text-red-400", bg: "bg-red-600/10 border-red-700/30" },
  { key: "detect", label: "Blue Team Detects", icon: Search, color: "text-emerald-400", bg: "bg-emerald-600/10 border-emerald-700/30" },
  { key: "generate", label: "AI Generates Sigma Rule", icon: FileText, color: "text-blue-400", bg: "bg-blue-600/10 border-blue-700/30" },
  { key: "deploy", label: "Human Approves & Deploys", icon: ShieldCheck, color: "text-purple-400", bg: "bg-purple-600/10 border-purple-700/30" },
]

export function DetectionGapLoop() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-zinc-300">Detection Gap Loop</CardTitle>
          <Badge variant="info" className="text-[10px]">Self-Healing</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {/* Phase Flow */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          {phases.map((phase, idx) => (
            <div key={phase.key} className={cn("relative rounded-xl border p-4 text-center", phase.bg)}>
              <div className="flex justify-center mb-2">
                <phase.icon className={cn("h-6 w-6", phase.color)} />
              </div>
              <span className={cn("text-[11px] font-bold", phase.color)}>{phase.label}</span>
              {idx < phases.length - 1 && (
                <ArrowRight className="absolute -right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-600" />
              )}
            </div>
          ))}
        </div>

        {/* Current Gaps */}
        <div className="space-y-3">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Detection Gaps Identified</span>
          {detectionGaps.map((gap) => (
            <div
              key={gap.id}
              className={cn(
                "rounded-lg border p-4 transition-all",
                gap.deployed ? "border-emerald-800/30 bg-emerald-900/10" :
                gap.sigmaGenerated ? "border-blue-800/30 bg-blue-900/10" :
                "border-red-800/30 bg-red-900/10"
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-zinc-200">{gap.attackTechnique}</span>
                    {gap.deployed && <Badge variant="default" className="text-[9px] px-1">Covered</Badge>}
                    {!gap.detected && !gap.deployed && <Badge variant="destructive" className="text-[9px] px-1">Gap</Badge>}
                    {gap.sigmaGenerated && !gap.humanApproved && <Badge variant="warning" className="text-[9px] px-1">Awaiting Approval</Badge>}
                  </div>

                  <div className="flex items-center gap-4 mt-2 text-[11px]">
                    <span className={cn("flex items-center gap-1", gap.detected ? "text-emerald-400" : "text-red-400")}>
                      {gap.detected ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                      Detection
                    </span>
                    <span className={cn("flex items-center gap-1", gap.sigmaGenerated ? "text-blue-400" : "text-zinc-500")}>
                      {gap.sigmaGenerated ? <CheckCircle2 className="h-3 w-3" /> : <Loader2 className="h-3 w-3" />}
                      Sigma Rule
                    </span>
                    <span className={cn("flex items-center gap-1", gap.humanApproved ? "text-purple-400" : gap.sigmaGenerated ? "text-amber-400" : "text-zinc-500")}>
                      {gap.humanApproved ? <CheckCircle2 className="h-3 w-3" /> : gap.sigmaGenerated ? <Loader2 className="h-3 w-3 text-amber-400" /> : <XCircle className="h-3 w-3" />}
                      Human Approved
                    </span>
                    <span className={cn("flex items-center gap-1", gap.deployed ? "text-emerald-400" : "text-zinc-500")}>
                      {gap.deployed ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                      Deployed
                    </span>
                  </div>

                  {gap.sigmaRule && !gap.humanApproved && (
                    <div className="mt-3 flex items-center gap-3">
                      <Button size="sm" variant="default" className="h-8 text-[11px] gap-1.5">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        Approve & Deploy Sigma Rule
                      </Button>
                      <Button size="sm" variant="ghost" className="h-8 text-[11px]">
                        Review Rule
                      </Button>
                    </div>
                  )}
                </div>

                <span className="text-[10px] text-zinc-600 flex-shrink-0">
                  {new Date(gap.discoveredAt).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
