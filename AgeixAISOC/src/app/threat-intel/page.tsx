"use client"

import { useState, useEffect } from "react"
import { IOCFeed } from "@/components/threat-intel/ioc-feed"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Globe, Server, AlertTriangle, Shield, RefreshCw, Search } from "lucide-react"
import { cn } from "@/lib/utils"
import { enrichIOC, type EnrichmentResult } from "@/lib/api"
import { iocs } from "@/lib/mock-data"

// ── Enrichment Lookup Panel ────────────────────────────────────────────────

function EnrichmentLookup() {
  const [ioc, setIoc] = useState("")
  const [result, setResult] = useState<EnrichmentResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleEnrich() {
    if (!ioc.trim()) return
    setLoading(true)
    setError("")
    setResult(null)
    try {
      const data = await enrichIOC(ioc.trim())
      setResult(data)
    } catch (err: any) {
      setError(err.message || "Enrichment failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-cyan-400" />
          <CardTitle className="text-sm font-semibold text-zinc-300">WP2 IOC Enrichment Lookup</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2 mb-4">
          <input
            value={ioc}
            onChange={(e) => setIoc(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleEnrich()}
            placeholder="Enter IP, hash, or domain (e.g. 185.130.5.23)"
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-cyan-700"
          />
          <Button size="sm" onClick={handleEnrich} disabled={loading} className="gap-1.5 bg-cyan-600 hover:bg-cyan-500">
            <Globe className="h-3.5 w-3.5" />
            {loading ? "Enriching..." : "Enrich"}
          </Button>
        </div>

        {error && (
          <div className="rounded-lg border border-red-800/30 bg-red-900/10 px-4 py-3 text-sm text-red-400">{error}</div>
        )}

        {result && (
          <div className="rounded-lg border border-cyan-800/20 bg-cyan-900/5 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-zinc-200 font-mono">{result.ioc}</span>
              <Badge variant={result.is_malicious ? "critical" : "default"} className="text-[10px]">
                {result.is_malicious ? "MALICIOUS" : "CLEAN"}
              </Badge>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-zinc-500">Reputation</span>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <div className="h-2 w-12 rounded-full bg-zinc-800 overflow-hidden">
                    <div className={cn("h-full rounded-full", result.reputation_score >= 80 ? "bg-red-500" : result.reputation_score >= 50 ? "bg-amber-500" : "bg-emerald-500")} style={{ width: `${result.reputation_score}%` }} />
                  </div>
                  <span className="text-xs font-bold text-zinc-300">{result.reputation_score}/100</span>
                </div>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-zinc-500">Country</span>
                <p className="text-xs font-medium text-zinc-300 mt-0.5">{result.country}</p>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-zinc-500">MITRE</span>
                <p className="text-xs font-medium text-zinc-300 mt-0.5">{result.mitre_technique || "—"}</p>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-zinc-500">Sources</span>
                <p className="text-xs text-zinc-400 mt-0.5">{result.sources.join(", ")}</p>
              </div>
            </div>
            {result.related_campaigns.length > 0 && (
              <div>
                <span className="text-[10px] uppercase tracking-wider text-zinc-500">Related Campaigns</span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {result.related_campaigns.map((c) => (
                    <Badge key={c} variant="destructive" className="text-[10px]">{c}</Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── Threat Intel Page ──────────────────────────────────────────────────────

export default function ThreatIntelPage() {
  const criticalCount = iocs.filter((i) => i.severity === "Critical").length
  const highCount = iocs.filter((i) => i.severity === "High").length

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Globe className="h-6 w-6 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Threat Intelligence</h1>
          </div>
          <p className="text-sm text-zinc-500 mt-1">
            WP2 integration &middot; Live IoC feed from VirusTotal, AbuseIPDB, AlienVault OTX, MISP &middot; Enrichment API
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="critical" className="gap-1 px-2.5 py-1.5 text-[11px]">
            <AlertTriangle className="h-3 w-3" />
            {criticalCount} Critical
          </Badge>
          <Badge variant="destructive" className="gap-1 px-2.5 py-1.5 text-[11px]">
            {highCount} High
          </Badge>
          <Badge variant="secondary" className="gap-1 px-2.5 py-1.5 text-[11px]">
            {iocs.length} Total IoCs
          </Badge>
        </div>
      </div>

      <Separator className="bg-zinc-800/60" />

      {/* Enrichment Lookup */}
      <EnrichmentLookup />

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "IP Addresses", count: iocs.filter((i) => i.type === "IP").length, icon: Server, color: "text-emerald-400" },
          { label: "Domains", count: iocs.filter((i) => i.type === "Domain").length, icon: Globe, color: "text-blue-400" },
          { label: "File Hashes", count: iocs.filter((i) => i.type === "Hash").length, icon: Shield, color: "text-amber-400" },
          { label: "URLs", count: iocs.filter((i) => i.type === "URL").length, icon: AlertTriangle, color: "text-red-400" },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-900/60 border border-zinc-800">
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

      {/* IOC Feed */}
      <IOCFeed />
    </div>
  )
}
