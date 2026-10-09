"use client"

import { useRef, useEffect } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { Terminal } from "lucide-react"

export interface FeedEntry {
  source: "ueba" | "osint" | "agent" | "soar"
  message: string
  timestamp: string
}

const SOURCE_STYLES: Record<string, { label: string; dot: string; bg: string }> = {
  ueba: {
    label: "UEBA",
    dot: "bg-blue-500 shadow-[0_0_4px_rgba(59,130,246,0.5)]",
    bg: "bg-blue-500/10 border-blue-500/20",
  },
  osint: {
    label: "OSINT",
    dot: "bg-red-500 shadow-[0_0_4px_rgba(239,68,68,0.5)]",
    bg: "bg-red-500/10 border-red-500/20",
  },
  agent: {
    label: "AGENT",
    dot: "bg-emerald-500 shadow-[0_0_4px_rgba(52,211,153,0.5)]",
    bg: "bg-emerald-500/10 border-emerald-500/20",
  },
  soar: {
    label: "SOAR",
    dot: "bg-yellow-500 shadow-[0_0_4px_rgba(234,179,8,0.5)]",
    bg: "bg-yellow-500/10 border-yellow-500/20",
  },
}

export function UnifiedLiveFeed({ entries }: { entries: FeedEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [entries.length])

  return (
    <div className="rounded-xl border border-zinc-800/50 bg-zinc-950/80 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Terminal className="h-4 w-4 text-zinc-400" />
        <span className="text-sm font-semibold text-zinc-300">Multi-Source Live Feed</span>
        <span className="text-[10px] text-zinc-600 font-mono">{entries.length} events</span>
      </div>
      <ScrollArea className="h-[360px]">
        <div className="space-y-1 font-mono text-[11px] leading-relaxed">
          {entries.length === 0 && (
            <p className="text-zinc-700 text-center py-12 italic">Awaiting system telemetry...</p>
          )}
          {entries.map((entry, i) => {
            const style = SOURCE_STYLES[entry.source]
            return (
              <div
                key={i}
                className={cn(
                  "flex items-start gap-2 px-2 py-1.5 rounded border border-transparent transition-colors hover:opacity-90",
                  style?.bg,
                )}
              >
                {/* Source dot */}
                <span className={cn("mt-1.5 h-1.5 w-1.5 rounded-full flex-shrink-0", style?.dot)} />

                {/* Timestamp */}
                <span className="text-zinc-600 flex-shrink-0 w-16">
                  {entry.timestamp
                    ? new Date(entry.timestamp).toLocaleTimeString("en-US", { hour12: false })
                    : ""}
                </span>

                {/* Source label */}
                <span
                  className={cn(
                    "flex-shrink-0 w-12 text-[10px] font-bold uppercase tracking-wider",
                    style?.dot.replace("bg-", "text-").replace(" shadow-*", ""),
                  )}
                  style={{
                    color: entry.source === "ueba" ? "#3b82f6" : entry.source === "osint" ? "#ef4444" : entry.source === "agent" ? "#34d399" : "#eab308",
                  }}
                >
                  {style?.label}
                </span>

                {/* Message */}
                <span className="text-zinc-400 break-words min-w-0">{entry.message}</span>
              </div>
            )
          })}
        </div>
        <div ref={bottomRef} />
      </ScrollArea>
    </div>
  )
}
