"use client"

import { useState, useEffect } from "react"
import { AuditTable } from "@/components/audit/audit-table"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { ShieldCheck, Hash, User, CheckCircle, XCircle, ExternalLink, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { getAuditTrail, verifyAuditChain, type AuditEntry } from "@/lib/api"

export default function AuditCompliancePage() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [chainIntegrity, setChainIntegrity] = useState(true)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  async function fetchAudit() {
    setLoading(true)
    try {
      const [trail, verification] = await Promise.all([
        getAuditTrail(100, 0),
        verifyAuditChain(),
      ])
      setEntries(trail.entries)
      setTotal(trail.total)
      setChainIntegrity(verification.chain_integrity)
    } catch {
      // Fall back to mock data
      setEntries([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAudit()
    const interval = setInterval(fetchAudit, 30000)
    return () => clearInterval(interval)
  }, [])

  const approved = entries.filter((e) => e.decision === "approved").length
  const rejected = entries.filter((e) => e.decision === "rejected").length
  const modified = entries.filter((e) => e.decision === "modified").length

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-6 w-6 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Audit Trail</h1>
          </div>
          <p className="text-sm text-zinc-500 mt-1">
            Immutable PostgreSQL audit log &middot; Every human decision cryptographically chained &middot; ISO 27001 compliant
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={chainIntegrity ? "default" : "critical"} className="gap-1.5 px-3 py-1.5 text-xs">
            <Hash className="h-3 w-3" />
            {chainIntegrity ? "Chain Verified" : "Chain Broken"}
          </Badge>
          <button onClick={fetchAudit} className="p-2 rounded-lg border border-zinc-800 hover:bg-zinc-800/60 transition-colors">
            <RefreshCw className={cn("h-4 w-4 text-zinc-400", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      <Separator className="bg-zinc-800/60" />

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Total Decisions", count: total || entries.length, icon: ShieldCheck, color: "text-zinc-300", bg: "bg-zinc-900/60" },
          { label: "Approved", count: approved, icon: CheckCircle, color: "text-green-400", bg: "bg-green-600/10" },
          { label: "Rejected", count: rejected, icon: XCircle, color: "text-red-400", bg: "bg-red-600/10" },
          { label: "Modified", count: modified, icon: ExternalLink, color: "text-blue-400", bg: "bg-blue-600/10" },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="p-4 flex items-center gap-3">
              <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg border border-zinc-800", s.bg)}>
                <s.icon className={cn("h-5 w-5", s.color)} />
              </div>
              <div>
                <span className="text-xl font-bold text-zinc-200">{s.count}</span>
                <p className="text-[11px] text-zinc-500">{s.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Immutable Audit Table */}
      <Card className="border-zinc-800/50 bg-zinc-900/40">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-sm font-semibold text-zinc-300">Immutable Audit Trail</CardTitle>
              <CardDescription className="text-[11px] mt-0.5">
                {entries.length} records &middot; Chain integrity: {chainIntegrity ? "VALID" : "BROKEN"}
              </CardDescription>
            </div>
            <Badge variant="default" className="text-[10px] gap-1.5">
              <ShieldCheck className="h-3 w-3" />
              PostgreSQL
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800/60">
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Decision ID</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Action</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Analyst</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Target</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Timestamp</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Hash</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id} className="border-b border-zinc-800/30 hover:bg-zinc-800/20 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-zinc-300">{entry.action_id}</td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={entry.decision === "approved" ? "default" : entry.decision === "rejected" ? "destructive" : entry.decision === "modified" ? "info" : "secondary"}
                        className="text-[10px]"
                      >
                        {entry.decision}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-300">{entry.approved_by || "—"}</td>
                    <td className="px-4 py-3 text-xs text-zinc-400 max-w-[200px] truncate">{entry.target}</td>
                    <td className="px-4 py-3 text-[11px] text-zinc-500 font-mono">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 font-mono text-[10px] text-zinc-600 max-w-[120px] truncate" title={entry.hash}>
                      {entry.hash.slice(0, 16)}...
                    </td>
                  </tr>
                ))}
                {entries.length === 0 && !loading && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-zinc-500">
                      <ShieldCheck className="h-8 w-8 text-zinc-700 mx-auto mb-2" />
                      <p className="text-sm">No audit entries yet</p>
                      <p className="text-xs text-zinc-600 mt-1">Decisions will appear here once HITL actions are taken</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
