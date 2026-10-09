"use client"

import { useState, useRef } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Search, Globe, Shield, Loader2, ChevronDown, ChevronUp, ScanLine, AlertTriangle, CheckCircle } from "lucide-react"

// ── Mock responses per search query type ────────────────────────────────────

interface SearchResult {
  query: string
  elapsed: string
  agents: string[]
  summary: string
  findings: Array<{ title: string; severity: string; source: string }>
}

function mockSearchResults(query: string): SearchResult {
  const isHash = /^[a-f0-9]{32,}$/i.test(query) || /^[a-f0-9]{40,}$/i.test(query)
  const isIp = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(query)
  const isDomain = /^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}$/i.test(query)

  if (isIp) {
    return {
      query,
      elapsed: "1.8s",
      agents: ["Threat Hunter", "Threat Detection", "Master Brain"],
      summary: `IP ${query} identified as malicious C2 infrastructure. 3 threat reports found. Associated with Emotet botnet and APT29 phishing campaigns. Reputation score: 94/100.`,
      findings: [
        { title: "185.130.5.x range associated with Emotet C2 — AlienVault OTX pulse updated 2h ago", severity: "CRITICAL", source: "DuckDuckGo" },
        { title: "CISA Alert AA26-194: APT29 using compromised VPN appliances for initial access", severity: "HIGH", source: "DuckDuckGo" },
        { title: "VirusTotal: 18/70 engines detected malicious activity from this IP", severity: "MEDIUM", source: "DuckDuckGo" },
      ],
    }
  }
  if (isHash) {
    return {
      query,
      elapsed: "2.3s",
      agents: ["Threat Hunter", "Threat Detection", "Risk Scoring"],
      summary: `File hash ${query.slice(0, 16)}... identified as a known malware variant. Linked to BlackCat/ALPHV ransomware campaigns. Sandbox analysis confirms data encryption behavior.`,
      findings: [
        { title: "Hash matches BlackCat ransomware sample (SHA256) — MITRE T1486", severity: "CRITICAL", source: "DuckDuckGo" },
        { title: "Recorded Future: similar hash family targets finance sector via spear-phishing", severity: "HIGH", source: "DuckDuckGo" },
        { title: "Hybrid Analysis: 28/40 sandbox engines flag as malicious — T1490 observed", severity: "MEDIUM", source: "DuckDuckGo" },
      ],
    }
  }
  if (isDomain) {
    return {
      query,
      elapsed: "1.5s",
      agents: ["Threat Hunter", "Threat Detection"],
      summary: `Domain ${query} identified as a phishing infrastructure host. 12 lookalike domains registered in the past 48 hours. SSL certificate issued 3 days ago.`,
      findings: [
        { title: "Domain registered 72h ago via anonymous registrar — common phishing TTP", severity: "CRITICAL", source: "DuckDuckGo" },
        { title: "URLScan.io: 4 pages detected mimicking Okta login portal", severity: "HIGH", source: "DuckDuckGo" },
      ],
    }
  }
  // Generic
  return {
    query,
    elapsed: "2.0s",
    agents: ["Threat Hunter", "Threat Detection", "Risk Scoring", "Master Brain"],
    summary: `OSINT search for "${query}" completed. Cross-referenced 3 intelligence feeds. 2 relevant threat reports found. No immediate CRITICAL correlation.`,
    findings: [
      { title: `Search results for "${query}" — 2 articles mentioning recent exploit activity`, severity: "MEDIUM", source: "DuckDuckGo" },
      { title: "Similar TTPs observed in FIN7 campaigns — MITRE T1190, T1110", severity: "MEDIUM", source: "DuckDuckGo" },
    ],
  }
}

function severityBadge(severity: string) {
  const map: Record<string, "critical" | "destructive" | "warning" | "default"> = {
    CRITICAL: "critical", HIGH: "destructive", MEDIUM: "warning", LOW: "default",
  }
  return map[severity] || "default"
}

// ── Search Animation ────────────────────────────────────────────────────────

function SearchAnimation({ agents, onComplete }: { agents: string[]; onComplete: () => void }) {
  const [phase, setPhase] = useState<"connecting" | "searching" | "correlating">("connecting")
  const [agentIdx, setAgentIdx] = useState(0)

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  if (phase === "connecting") {
    timerRef.current = setTimeout(() => setPhase("searching"), 600)
    return (
      <div className="flex items-center gap-3 py-4 text-sm text-zinc-400">
        <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
        Agents are connecting to intelligence feeds...
      </div>
    )
  }

  if (phase === "searching") {
    if (agentIdx < agents.length) {
      timerRef.current = setTimeout(() => setAgentIdx((i) => i + 1), 800)
      return (
        <div className="space-y-2 py-3">
          {agents.slice(0, agentIdx + 1).map((agent, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              {i === agentIdx ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />
              ) : (
                <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
              )}
              <span className={cn(i === agentIdx ? "text-amber-400" : "text-emerald-400")}>{agent}</span>
              <span className="text-xs text-zinc-600">
                {i === agentIdx ? "scouring the web..." : "search complete"}
              </span>
            </div>
          ))}
        </div>
      )
    }
    // All agents done
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setPhase("correlating"), 300)
  }

  if (phase === "correlating") {
    timerRef.current = setTimeout(onComplete, 500)
    return (
      <div className="flex items-center gap-3 py-3 text-sm text-zinc-400">
        <ScanLine className="h-4 w-4 animate-pulse text-violet-400" />
        Master Brain correlating findings...
      </div>
    )
  }

  return null
}

// ── Main Component ──────────────────────────────────────────────────────────

export function QuickSearch() {
  const [query, setQuery] = useState("")
  const [searching, setSearching] = useState(false)
  const [animating, setAnimating] = useState(false)
  const [result, setResult] = useState<SearchResult | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [error, setError] = useState("")

  const handleSearch = () => {
    const trimmed = query.trim()
    if (!trimmed) {
      setError("Enter an IP, hash, domain, or keyword")
      return
    }
    setError("")
    setResult(null)
    setSearching(true)
    setAnimating(true)
    setExpanded(false)
  }

  const handleAnimationComplete = () => {
    setAnimating(false)
    setSearching(false)
    setResult(mockSearchResults(query.trim()))
    setExpanded(true)
  }

  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-600 to-cyan-600 shadow-lg">
            <Search className="h-4 w-4 text-white" />
          </div>
          <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">AgeixAI Quick Search</span>
          <div className="flex-1 flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Enter IP (e.g. 185.130.5.23), file hash, domain, or keyword..."
              disabled={searching}
              className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-700 disabled:opacity-50"
            />
            <Button
              onClick={handleSearch}
              disabled={searching || !query.trim()}
              className="gap-1.5 bg-emerald-600 hover:bg-emerald-500 h-9 text-xs disabled:opacity-50"
            >
              {searching && animating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Globe className="h-3.5 w-3.5" />
              )}
              {searching && animating ? "Searching..." : "Search"}
            </Button>
          </div>
        </div>

        {error && <p className="text-xs text-red-400 mt-2">{error}</p>}

        {/* Loading Animation */}
        {searching && animating && result === null && (
          <div className="mt-3 rounded-lg border border-zinc-800/30 bg-zinc-800/20 px-4">
            <SearchAnimation agents={["Threat Hunter", "Threat Detection", "Risk Scoring", "Master Brain"]} onComplete={handleAnimationComplete} />
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="mt-3 rounded-lg border border-emerald-800/30 bg-emerald-900/5 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-emerald-800/20">
              <div className="flex items-center gap-2">
                <Globe className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-[10px] font-semibold uppercase text-emerald-400">Web Search Complete</span>
                <Badge variant="default" className="text-[10px] px-1 bg-emerald-600/10 text-emerald-400 border-emerald-700/30">
                  {result.elapsed}
                </Badge>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1 text-zinc-500 hover:text-zinc-300"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              </Button>
            </div>

            <div className="px-4 py-3">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="h-3.5 w-3.5 text-zinc-500" />
                <span className="text-xs text-zinc-400">{result.summary}</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-zinc-600">
                <span>Agents: {result.agents.join(", ")}</span>
              </div>
            </div>

            {expanded && (
              <div className="border-t border-emerald-800/20 px-4 py-3 space-y-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Findings</span>
                {result.findings.map((f, i) => (
                  <div key={i} className="flex items-start gap-2 rounded-lg border border-zinc-800/20 bg-zinc-800/15 px-3 py-2">
                    <AlertTriangle className={cn(
                      "h-3.5 w-3.5 mt-0.5 flex-shrink-0",
                      f.severity === "CRITICAL" ? "text-red-400" : f.severity === "HIGH" ? "text-orange-400" : "text-yellow-400",
                    )} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-zinc-300">{f.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant={severityBadge(f.severity)} className="text-[9px] px-1 py-0">{f.severity}</Badge>
                        <span className="text-[9px] text-zinc-600">{f.source}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
