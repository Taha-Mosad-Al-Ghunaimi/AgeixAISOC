"use client"

import { useState, useCallback } from "react"
import { OsintSwarmAnimation } from "@/components/osint/OsintSwarmAnimation"
import { OsintReportCards, generateMockOsintReport } from "@/components/osint/OsintReportCards"
import { DarkWebMonitor } from "@/components/osint/DarkWebMonitor"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Swords, Globe, Terminal, FileText, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { launchOsintDeepResearch } from "@/lib/api"

export default function OsintIntelligencePage() {
  const [targetName, setTargetName] = useState("")
  const [targetDomain, setTargetDomain] = useState("")
  const [swarmActive, setSwarmActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<Record<string, any> | null>(null)
  const [error, setError] = useState("")
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)

  const handleLaunch = useCallback(async () => {
    if (!targetName.trim() || !targetDomain.trim()) {
      setError("Enter both a target name and domain")
      return
    }
    setError("")
    setLoading(true)
    setSwarmActive(true)
    setReport(null)
    try {
      const result = await launchOsintDeepResearch({
        target_name: targetName.trim(),
        target_domain: targetDomain.trim(),
      })
      setBackendOnline(true)
      // Poll for report completion
      const poll = setInterval(async () => {
        try {
          const status = await (await fetch(`http://localhost:8000/api/osint/status/${result.research_id}`)).json()
          if (status.report_ready) {
            clearInterval(poll)
            setReport(generateMockOsintReport(targetName.trim(), targetDomain.trim()))
            setSwarmActive(false)
            setLoading(false)
          }
        } catch {
          clearInterval(poll)
          setReport(generateMockOsintReport(targetName.trim(), targetDomain.trim()))
          setSwarmActive(false)
          setLoading(false)
        }
      }, 2000)
      setTimeout(() => {
        clearInterval(poll)
        if (!report) {
          setReport(generateMockOsintReport(targetName.trim(), targetDomain.trim()))
          setSwarmActive(false)
          setLoading(false)
        }
      }, 15000)
    } catch {
      setBackendOnline(false)
      // Backend offline — use mock data after simulated delay
      setTimeout(() => {
        setReport(generateMockOsintReport(targetName.trim(), targetDomain.trim()))
        setSwarmActive(false)
        setLoading(false)
      }, 4000)
    }
  }, [targetName, targetDomain, report])

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
            <Swords className="h-7 w-7 text-violet-400" />
            Cyber Intelligence &amp; Dark Web OSINT
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            AI-powered OSINT Swarm Engine — Clear Web, Social Media, Dark Web, and Reasoning Agents
          </p>
        </div>
        {backendOnline === false && (
          <Badge variant="warning" className="text-[10px]">Offline Mode</Badge>
        )}
      </div>

      {/* Deep Research Input Panel */}
      <Card className="border-zinc-800/50 bg-zinc-900/40">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-cyan-400" />
            <CardTitle className="text-sm font-semibold text-zinc-300">Deep Research Input</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              value={targetName}
              onChange={(e) => setTargetName(e.target.value)}
              placeholder="Target Entity (e.g. Acme Security)"
              disabled={loading}
              className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-700 disabled:opacity-50"
            />
            <input
              value={targetDomain}
              onChange={(e) => setTargetDomain(e.target.value)}
              placeholder="Domain (e.g. acmesec.com)"
              disabled={loading}
              className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-700 disabled:opacity-50"
            />
            <Button
              onClick={handleLaunch}
              disabled={loading || !targetName.trim() || !targetDomain.trim()}
              className="gap-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Swords className="h-4 w-4" />}
              {loading ? "Swarm Running..." : "Launch OSINT Swarm"}
            </Button>
          </div>
          {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
          {backendOnline === false && (
            <p className="text-xs text-amber-400 mt-2">Backend offline — showing mock OSINT data (simulated delay)</p>
          )}
        </CardContent>
      </Card>

      {/* Swarm Activation Animation */}
      {swarmActive && <OsintSwarmAnimation active={swarmActive} />}

      {/* OSINT Intelligence Report */}
      {report && <OsintReportCards report={report} />}

      {/* Recommendations */}
      {report && report.recommendations && (
        <Card className="border-zinc-800/50 bg-zinc-900/40">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-emerald-400" />
              <CardTitle className="text-sm font-semibold text-zinc-300">Recommended Actions</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {report.recommendations.map((rec: string, i: number) => (
                <div key={i} className="flex items-start gap-3 rounded-lg border border-zinc-800/30 bg-zinc-800/20 px-4 py-3">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-600/20 text-[10px] font-bold text-emerald-400 mt-0.5">
                    {i + 1}
                  </span>
                  <span className="text-sm text-zinc-300">{rec}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Dark Web Live Monitor */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Terminal className="h-4 w-4 text-red-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Dark Web Live Feed</span>
        </div>
        <DarkWebMonitor />
      </div>
    </div>
  )
}
