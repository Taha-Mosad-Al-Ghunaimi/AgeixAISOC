"use client"

import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

const MOCK_ALERTS = [
  { message: "New paste on Ahmia: acmesec.com user database — 1,247 credentials leaked", severity: "critical" },
  { message: "Telegram channel 'LeakDB' posted acmesec.com VPN credentials (34 entries)", severity: "high" },
  { message: "Ransomware blog: 'Acme Security' listed — 1.2TB data exfiltrated", severity: "critical" },
  { message: "Dark web forum thread: 'Selling RDP access to Acme Security — domain admin'", severity: "high" },
  { message: "Pastebin: acmesec.com employee list published — 89 names with roles", severity: "medium" },
  { message: "ZeroDay forum: Acme Security custom app exploit (RCE) for sale — $150K", severity: "critical" },
  { message: "Telegram: Acme Security internal credentials being auctioned — starting at 0.5 BTC", severity: "high" },
  { message: "New Ahmia paste: acmesec.com — database_config.yml with passwords", severity: "high" },
  { message: "Ransomware group 'LockBit' claims Acme Security breach — negotiating ransom", severity: "critical" },
  { message: "Pastebin: acmesec.com — AWS keys (AKIA*) found in public paste", severity: "medium" },
  { message: "Breach forum: Acme Security employee credentials verified — 442 active accounts", severity: "critical" },
  { message: "Telegram channel selling Acme Security customer database — 15K records", severity: "high" },
]

const severityColor = {
  critical: "text-red-400",
  high: "text-orange-400",
  medium: "text-yellow-400",
}

export function DarkWebMonitor() {
  const [alerts, setAlerts] = useState<Array<{ id: number; message: string; severity: string; timestamp: string }>>([])
  const [connected, setConnected] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const alertId = useRef(0)

  useEffect(() => {
    // Simulate WebSocket connection
    setConnected(true)
    const interval = setInterval(() => {
      const alert = MOCK_ALERTS[Math.floor(Math.random() * MOCK_ALERTS.length)]
      alertId.current++
      setAlerts((prev) => {
        const next = [...prev, { id: alertId.current, ...alert, timestamp: new Date().toLocaleTimeString() }]
        return next.slice(-50)
      })
    }, 2500 + Math.random() * 3000)
    return () => { clearInterval(interval); setConnected(false) }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [alerts])

  return (
    <div className="rounded-xl border border-zinc-800/50 bg-zinc-950 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800/50 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <div className={cn("flex h-2 w-2", connected && "animate-pulse")}>
            <span className={cn(
              "absolute inline-flex h-2 w-2 rounded-full",
              connected ? "bg-emerald-500" : "bg-zinc-600",
            )} />
          </div>
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Dark Web Live Monitor</span>
          <span className="text-[10px] text-zinc-600">({alerts.length} alerts)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn(
            "text-[10px] font-medium",
            connected ? "text-emerald-500" : "text-zinc-600",
          )}>
            {connected ? "CONNECTED" : "DISCONNECTED"}
          </span>
          {connected && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />}
        </div>
      </div>

      {/* Terminal content */}
      <div className="h-48 overflow-y-auto p-3 font-mono text-xs leading-relaxed bg-[#0a0a0b]">
        {alerts.length === 0 && (
          <div className="text-zinc-700 italic">Waiting for dark web intelligence feed...</div>
        )}
        {alerts.map((alert) => (
          <div key={alert.id} className="mb-1.5 animate-in slide-in-from-bottom-1 duration-200">
            <span className="text-zinc-700">[{alert.timestamp}]</span>{" "}
            <span className={cn("font-medium", severityColor[alert.severity as keyof typeof severityColor] || "text-zinc-400")}>
              [ALERT{alert.severity === "critical" ? "!" : ""}]
            </span>{" "}
            <span className={cn(severityColor[alert.severity as keyof typeof severityColor] || "text-zinc-400")}>
              {alert.message}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
