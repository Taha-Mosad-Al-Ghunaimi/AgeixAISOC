"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { Globe, Users, Skull, Share2 } from "lucide-react"

// ── Mock OSINT Report (fallback when backend offline) ──────────────────────

export function generateMockOsintReport(targetName: string, targetDomain: string): Record<string, any> {
  const now = new Date().toISOString()
  return {
    target: targetName,
    target_domain: targetDomain,
    risk_score: Math.floor(Math.random() * 40) + 45,
    risk_level: "high",
    summary: `OSINT deep research for ${targetName} (${targetDomain}) reveals ${Math.floor(Math.random() * 5) + 3} exposed assets, ${Math.floor(Math.random() * 200) + 50} leaked credentials on the dark web, and potential ransomware interest from LockBit affiliates. Immediate remediation recommended.`,
    sources_analyzed: 3,
    total_findings: 12,
    false_positives_removed: 2,
    credentials_exposed: Math.floor(Math.random() * 500) + 100,
    credentials_at_risk: true,
    ransomware_mentions: true,
    zero_day_discussions: Math.random() > 0.5,
    top_risks: [
      { risk: `Open S3 bucket with database backups at ${targetDomain}-backup.s3.amazonaws.com`, severity: "CRITICAL", source: "clear_web" },
      { risk: `VPN credentials for ${targetDomain} found on Telegram criminal channel (45K subscribers)`, severity: "CRITICAL", source: "dark_web" },
      { risk: "SOC team reportedly understaffed (Glassdoor reviews)", severity: "MEDIUM", source: "social_media" },
      { risk: `Jenkins CI at https://jenkins.${targetDomain} accessible without authentication`, severity: "HIGH", source: "clear_web" },
    ],
    recommendations: [
      "Immediately secure exposed S3 bucket and rotate all database credentials",
      "Enforce MFA on all VPN accounts and rotate existing credentials",
      "Conduct phishing simulation targeting employees whose credentials were found on dark web",
      "Review and restrict public-facing Confluence and Jenkins instances",
      "Increase SOC headcount per Glassdoor feedback",
    ],
    dark_web_intel_summary: `Multiple credential dumps found for ${targetDomain}. ${Math.floor(Math.random() * 3) + 1} ransomware groups discussing the target. IAB listing offering RDP access for 3 BTC.`,
    clear_web_exposures: [
      `Public Confluence wiki at https://confluence.${targetDomain} with network diagrams`,
      `Open S3 bucket at ${targetDomain}-backup.s3.amazonaws.com containing DB backups (~2.4GB)`,
      `Jenkins CI at https://jenkins.${targetDomain} accessible without authentication`,
      `Employee directory exposed on company about page`,
    ],
    social_media_insights: [
      `VP of Engineering publicly identified on LinkedIn — potential phishing target`,
      "Glassdoor reviews suggest understaffed security team (avg 3.8 rating)",
      `Open roles for Senior Cloud Security Engineer indicate possible turnover`,
    ],
    generated_at: now,
  }
}

// ── Props ──────────────────────────────────────────────────────────────────

interface Props {
  report: Record<string, any>
}

// ── Section: Executive Summary ─────────────────────────────────────────────

function ExecutiveSummaryCard({ report }: { report: Record<string, any> }) {
  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Globe className="h-4 w-4 text-emerald-400" />
          <CardTitle className="text-sm font-semibold text-zinc-300">Executive Summary</CardTitle>
          <Badge variant={report.risk_level === "critical" ? "critical" : report.risk_level === "high" ? "destructive" : "warning"} className="ml-auto text-[10px]">
            {report.risk_level.toUpperCase()} RISK
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className="font-mono">{report.target_domain}</span>
          <span>·</span>
          <span>{report.total_findings} findings</span>
          <span>·</span>
          <span>{report.false_positives_removed} FP removed</span>
        </div>
        <p className="text-sm leading-relaxed text-zinc-400">{report.summary}</p>
        <div className="flex gap-4 pt-1">
          <div>
            <span className="text-[10px] uppercase tracking-wider text-zinc-600">Risk Score</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <div className="h-2 w-20 rounded-full bg-zinc-800 overflow-hidden">
                <div className={cn("h-full rounded-full", report.risk_score >= 70 ? "bg-red-500" : report.risk_score >= 40 ? "bg-amber-500" : "bg-emerald-500")} style={{ width: `${report.risk_score}%` }} />
              </div>
              <span className="text-xs font-bold text-zinc-300">{report.risk_score}/100</span>
            </div>
          </div>
          <div>
            <span className="text-[10px] uppercase tracking-wider text-zinc-600">Credentials Exposed</span>
            <p className="text-sm font-bold text-red-400 mt-0.5">{report.credentials_exposed.toLocaleString()}</p>
          </div>
          <div>
            <span className="text-[10px] uppercase tracking-wider text-zinc-600">Ransomware</span>
            <p className={cn("text-sm font-bold mt-0.5", report.ransomware_mentions ? "text-red-400" : "text-emerald-400")}>
              {report.ransomware_mentions ? "Detected" : "None"}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Section: Digital Footprint (Social Media) ──────────────────────────────

function DigitalFootprintCard({ report }: { report: Record<string, any> }) {
  const insights = report.social_media_insights || []
  const exposures = report.clear_web_exposures || []

  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-cyan-400" />
          <CardTitle className="text-sm font-semibold text-zinc-300">Digital Footprint</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <span className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2 block">Social Media Intelligence</span>
          <div className="space-y-2">
            {insights.map((insight: string, i: number) => (
              <div key={i} className="flex items-start gap-2 rounded-lg border border-zinc-800/30 bg-zinc-800/20 px-3 py-2">
                <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-cyan-500" />
                <span className="text-xs text-zinc-400">{insight}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2 block">Exposed Web Assets</span>
          <div className="space-y-1.5">
            {exposures.slice(0, 3).map((exp: string, i: number) => (
              <div key={i} className="flex items-center gap-2 rounded px-2 py-1.5 text-xs text-zinc-500 font-mono bg-zinc-800/10">
                <span className="h-1 w-1 rounded-full bg-amber-500" />
                {exp}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Section: Dark Web Exposure ─────────────────────────────────────────────

function DarkWebExposureCard({ report }: { report: Record<string, any> }) {
  const risks = report.top_risks || []
  const darkRisks = risks.filter((r: any) => r.source === "dark_web")

  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Skull className="h-4 w-4 text-violet-400" />
          <CardTitle className="text-sm font-semibold text-zinc-300">Dark Web Exposure</CardTitle>
          {report.ransomware_mentions && (
            <Badge variant="critical" className="ml-auto text-[10px]">RANSOMWARE</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs leading-relaxed text-zinc-400">{report.dark_web_intel_summary}</p>

        <div className="rounded-lg border border-violet-800/20 bg-violet-900/5 p-3">
          <span className="text-[10px] uppercase tracking-wider text-violet-400 block mb-2">Leaked Credentials</span>
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold text-red-400">{report.credentials_exposed.toLocaleString()}</span>
            <span className="text-xs text-zinc-500">passwords exposed</span>
          </div>
        </div>

        {darkRisks.length > 0 && (
          <div>
            <span className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2 block">Dark Web Findings</span>
            <div className="space-y-2">
              {darkRisks.map((r: any, i: number) => (
                <div key={i} className="flex items-start gap-2 rounded-lg border border-violet-800/20 bg-violet-900/5 px-3 py-2">
                  <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-violet-500" />
                  <div>
                    <p className="text-xs text-zinc-300">{r.risk}</p>
                    <Badge variant="critical" className="mt-1 text-[10px]">{r.severity}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {report.zero_day_discussions && (
          <div className="rounded-lg border border-red-800/20 bg-red-900/10 px-3 py-2">
            <span className="text-[10px] font-semibold text-red-400">⚠ Zero-Day Exploit Discussion Detected</span>
            <p className="text-xs text-zinc-500 mt-1">Threat actors are discussing unpatched vulnerabilities targeting this organization. Elevated monitoring recommended.</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── Section: Link Analysis ─────────────────────────────────────────────────

function LinkAnalysisCard({ report }: { report: Record<string, any> }) {
  const exposures = report.clear_web_exposures || []
  const insights = report.social_media_insights || []
  const risks = report.top_risks || []
  const darkRisks = risks.filter((r: any) => r.source === "dark_web")

  // Build nodes for the visual graph
  const nodes = [
    { id: "target", label: report.target?.slice(0, 12) || "Target", cx: 50, cy: 15, color: "#10b981" },
    { id: "web", label: "Web", cx: 15, cy: 50, color: "#06b6d4" },
    { id: "social", label: "Social", cx: 40, cy: 75, color: "#f59e0b" },
    { id: "dark", label: "Dark Web", cx: 75, cy: 50, color: "#8b5cf6" },
    { id: "cred", label: "Leaks", cx: 85, cy: 80, color: "#ef4444" },
  ]

  const edges = [
    { from: "web", to: "target" },
    { from: "social", to: "target" },
    { from: "dark", to: "target" },
    { from: "dark", to: "cred" },
    { from: "web", to: "social" },
  ]

  return (
    <Card className="border-zinc-800/50 bg-zinc-900/40">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Share2 className="h-4 w-4 text-amber-400" />
          <CardTitle className="text-sm font-semibold text-zinc-300">Link Analysis</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <svg viewBox="0 0 100 90" className="w-full h-48">
          {/* Edges */}
          {edges.map((edge, i) => {
            const from = nodes.find((n) => n.id === edge.from)
            const to = nodes.find((n) => n.id === edge.to)
            if (!from || !to) return null
            return (
              <line
                key={i}
                x1={from.cx} y1={from.cy} x2={to.cx} y2={to.cy}
                stroke="#3f3f46" strokeWidth="0.6" strokeDasharray="1.5 1.5"
              />
            )
          })}
          {/* Nodes */}
          {nodes.map((node) => (
            <g key={node.id}>
              <circle cx={node.cx} cy={node.cy} r="4" fill={node.color} className="drop-shadow-lg" />
              <text x={node.cx} y={node.cy - 6} textAnchor="middle" fill="#a1a1aa" fontSize="3" fontWeight="600">{node.label}</text>
            </g>
          ))}
        </svg>

        {/* Legend */}
        <div className="grid grid-cols-2 gap-2 mt-2">
          <div className="flex items-center gap-1.5 text-[10px] text-zinc-600">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> {exposures.length} Web Assets
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-zinc-600">
            <span className="h-2 w-2 rounded-full bg-amber-500" /> {insights.length} Social Intel
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-zinc-600">
            <span className="h-2 w-2 rounded-full bg-violet-500" /> {darkRisks.length} Dark Web hits
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-zinc-600">
            <span className="h-2 w-2 rounded-full bg-red-500" /> {report.credentials_exposed.toLocaleString()} Credentials
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Main Composite ─────────────────────────────────────────────────────────

export function OsintReportCards({ report }: Props) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <ExecutiveSummaryCard report={report} />
      <DigitalFootprintCard report={report} />
      <DarkWebExposureCard report={report} />
      <LinkAnalysisCard report={report} />
    </div>
  )
}
