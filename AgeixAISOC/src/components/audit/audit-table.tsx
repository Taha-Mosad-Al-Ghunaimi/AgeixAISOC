"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { auditEntries } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { CheckCircle, XCircle, ExternalLink, Hash, User, Clock, Shield } from "lucide-react"

const actionConfig = {
  Approved: { badge: "default" as const, icon: CheckCircle, color: "text-green-400" },
  Rejected: { badge: "destructive" as const, icon: XCircle, color: "text-red-400" },
  Modified: { badge: "info" as const, icon: ExternalLink, color: "text-blue-400" },
  Pending: { badge: "secondary" as const, icon: Clock, color: "text-yellow-400" },
}

export function AuditTable() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-zinc-300">Immutable Audit Trail</CardTitle>
            <CardDescription className="text-[11px] mt-0.5">
              Every human decision is cryptographically anchored &middot; {auditEntries.length} records
            </CardDescription>
          </div>
          <Badge variant="default" className="text-[10px] gap-1.5">
            <Shield className="h-3 w-3" />
            Blockchain Verified
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[600px]">
          <div className="px-4 pb-4 space-y-3">
            {auditEntries.map((entry, idx) => {
              const action = actionConfig[entry.action]
              return (
                <div
                  key={entry.id}
                  className={cn(
                    "rounded-xl border p-4 transition-all hover:bg-zinc-800/20",
                    entry.action === "Approved" ? "border-green-900/30" :
                    entry.action === "Rejected" ? "border-red-900/30" :
                    "border-blue-900/30"
                  )}
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg",
                        entry.action === "Approved" ? "bg-green-600/15" :
                        entry.action === "Rejected" ? "bg-red-600/15" :
                        "bg-blue-600/15"
                      )}>
                        <action.icon className={cn("h-4 w-4", action.color)} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-zinc-200">{entry.title}</span>
                          <Badge variant={action.badge} className="text-[9px] px-1.5">
                            {entry.action}
                          </Badge>
                        </div>
                        <span className="text-[11px] text-zinc-500">{entry.decisionId}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 text-[11px] text-zinc-500">
                      <Clock className="h-3 w-3" />
                      {new Date(entry.timestamp).toLocaleString()}
                    </div>
                  </div>

                  {/* Details */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                    <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
                      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500 mb-1">
                        <User className="h-3 w-3" /> Analyst
                      </div>
                      <span className="text-sm font-medium text-zinc-300">{entry.analystName}</span>
                    </div>
                    <div className="rounded-lg bg-zinc-900/60 px-3 py-2 border border-zinc-800/40">
                      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500 mb-1">
                        <Hash className="h-3 w-3" /> Block Number
                      </div>
                      <span className="text-sm font-mono font-medium text-zinc-300">#{entry.blockNumber}</span>
                    </div>
                  </div>

                  {/* Recommendation */}
                  <div className="mb-2">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Original Recommendation</span>
                    <p className="text-xs text-zinc-400 mt-0.5">{entry.originalRecommendation}</p>
                  </div>

                  {entry.action === "Modified" && entry.modifiedAction && (
                    <div className="mb-2">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-400">Modified Action</span>
                      <p className="text-xs text-blue-300 mt-0.5">{entry.modifiedAction}</p>
                    </div>
                  )}

                  {entry.notes && (
                    <div className="rounded-lg bg-zinc-900/40 px-3 py-2 border border-zinc-800/40">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Analyst Notes</span>
                      <p className="text-xs text-zinc-400 mt-0.5 italic">"{entry.notes}"</p>
                    </div>
                  )}

                  {/* Immutable Hash */}
                  <div className="mt-3 pt-3 border-t border-zinc-800/40">
                    <div className="flex items-center gap-2">
                      <Hash className="h-3 w-3 text-zinc-600" />
                      <span className="text-[10px] font-mono text-zinc-600 truncate">{entry.immutableHash}</span>
                    </div>
                  </div>

                  {idx < auditEntries.length - 1 && <Separator className="mt-4 bg-zinc-800/30" />}
                </div>
              )
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
