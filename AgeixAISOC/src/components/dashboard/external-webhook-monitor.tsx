"use client"

import { useEffect, useRef, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { Webhook, CheckCircle2, Clock, Loader2 } from "lucide-react"

const MOCK_SOURCES = ["Github Dependabot", "Snyk", "Jenkins CI", "Custom Scanner", "GitLab SAST", "CrowdStrike", "SentinelOne"]

const MOCK_DESCRIPTIONS = [
  "Critical vulnerability in lodash@4.17.21 — CVE-2025-44228",
  "Open S3 bucket detected in production account",
  "Hardcoded API key found in src/config.py",
  "New container image with critical CVEs deployed",
  "TLS certificate expires in 7 days for api.example.com",
  "Dependency scan: 12 outdated packages with known vulns",
  "IAM policy grants *:* to anonymous principal",
]

const SAMPLE_QUERIES = [
  "Searching DuckDuckGo for: CVE-2025-44228 exploit in wild...",
  "Searching DuckDuckGo for: lodash prototype pollution CVE...",
  "Searching DuckDuckGo for: exposed S3 bucket incident reports...",
  "Searching DuckDuckGo for: hardcoded API key leak response...",
  "Searching DuckDuckGo for: container escape CVE techniques...",
  "Searching DuckDuckGo for: TLS misconfiguration exploitation...",
  "Searching DuckDuckGo for: IAM privilege escalation attacks...",
]

const SAMPLE_RESULTS = [
  "Found 3 articles linking to APT29 — Log4j + credential stuffing campaign reported by CISA",
  "MITRE ATT&CK T1190 — multiple IoT botnets exploiting recent CVEs in the wild",
  "ThreatFox pulse: 185.130.5.x associated with Emotet C2 infrastructure (updated 2h ago)",
  "AlienVault OTX: new BlackCat ransomware sample uses similar TTPs — T1486, T1490",
  "NVD: CVE-2025-44228 CVSS 9.8 — exploit available, 2 PoCs published on GitHub",
  "Recorded Future: FIN7 targeting finance sector via web app exploitation + SMB lateral movement",
  "CISA KEV added CVE-2026-3312 — actively exploited in the wild",
]

export function ExternalWebhookMonitor() {
  const [webhooks, setWebhooks] = useState<Array<{
    id: number; source: string; title: string; status: string; agent: string; timestamp: string
    queries: string[]; results: string[]; phase: string
  }>>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const idRef = useRef(0)

  useEffect(() => {
    const interval = setInterval(() => {
      idRef.current++
      const source = MOCK_SOURCES[Math.floor(Math.random() * MOCK_SOURCES.length)]
      const title = MOCK_DESCRIPTIONS[Math.floor(Math.random() * MOCK_DESCRIPTIONS.length)]
      const queryCount = Math.floor(Math.random() * 3) + 1
      const queries = Array.from({ length: queryCount }, () => SAMPLE_QUERIES[Math.floor(Math.random() * SAMPLE_QUERIES.length)])
      const results = Array.from({ length: queryCount }, () => SAMPLE_RESULTS[Math.floor(Math.random() * SAMPLE_RESULTS.length)])

      setWebhooks((prev) => {
        const next = [
          {
            id: idRef.current,
            source,
            title,
            status: "received",
            agent: "Threat Detection",
            timestamp: new Date().toLocaleTimeString(),
            queries,
            results,
            phase: "complete",
          },
          ...prev,
        ].slice(0, 30)
        return next
      })
    }, 4000 + Math.random() * 3000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [webhooks])

  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Webhook className="h-4 w-4 text-cyan-400" />
            <CardTitle className="text-sm font-semibold text-zinc-300">External Webhooks</CardTitle>
            <Badge variant="default" className="text-[10px] px-1.5 py-0">{webhooks.length}</Badge>
          </div>
          <span className="text-[10px] text-zinc-600">Live feed</span>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[280px]">
          <div className="space-y-1.5">
            {webhooks.length === 0 && (
              <p className="text-xs text-zinc-600 text-center py-10">Waiting for external webhooks...</p>
            )}
            {webhooks.map((wh) => (
              <div key={wh.id} className="flex items-start gap-2.5 rounded-lg border border-zinc-800/30 bg-zinc-800/15 px-3 py-2 transition-colors hover:bg-zinc-800/25">
                <div className="mt-0.5 flex-shrink-0">
                  {wh.status === "received" ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  ) : (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold text-cyan-400 uppercase">{wh.source}</span>
                    <Badge variant="default" className="text-[10px] px-1 bg-emerald-600/10 text-emerald-400 border-emerald-700/30">
                      Routed to {wh.agent}
                    </Badge>
                  </div>
                  <p className="text-xs text-zinc-400 truncate mt-0.5">{wh.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Clock className="h-3 w-3 text-zinc-600" />
                    <span className="text-[10px] text-zinc-600">{wh.timestamp}</span>
                  </div>
                  {wh.queries.length > 0 && (
                    <div className="mt-2 space-y-0.5">
                      {wh.queries.map((q, i) => (
                        <div key={i} className="flex items-start gap-1.5">
                          <span className="text-[9px] text-amber-500/70 font-mono mt-0.5">$</span>
                          <span className="text-[10px] text-zinc-500 font-mono leading-tight">{q}</span>
                        </div>
                      ))}
                      {wh.results.map((r, i) => (
                        <div key={i} className="flex items-start gap-1.5">
                          <span className="text-[9px] text-emerald-500/70 mt-0.5">▶</span>
                          <span className="text-[10px] text-zinc-500 font-mono leading-tight">{r}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
