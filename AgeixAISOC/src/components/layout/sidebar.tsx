"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  BrainCircuit,
  Swords,
  Globe,
  ShieldCheck,
  ChevronDown,
  Activity,
  Shield,
  AlertTriangle,
  Scan,
  Search,
  UserCheck,
  Bot,
} from "lucide-react"

const navItems = [
  {
    section: "Operations",
    items: [
      { href: "/command-center", label: "Command Center", icon: LayoutDashboard },
      { href: "/soc-automation", label: "SOC Automation Hub", icon: Bot },
    ],
  },
  {
    section: "AI & Intelligence",
    items: [
      { href: "/ai-brain", label: "AI Brain", icon: BrainCircuit },
      { href: "/threat-intel", label: "Threat Intel", icon: Globe },
      { href: "/osint-intelligence", label: "Cyber Intel", icon: UserCheck },
    ],
  },
  {
    section: "Investigation",
    items: [
      { href: "/incidents-forensics", label: "Incidents & Forensics", icon: Search },
    ],
  },
  {
    section: "Governance",
    items: [
      { href: "/audit-compliance", label: "Audit & Compliance", icon: ShieldCheck },
    ],
  },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-zinc-800/80 bg-zinc-950/95 backdrop-blur-xl">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-zinc-800/60 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-600 to-emerald-800 shadow-lg shadow-emerald-600/25">
          <Shield className="h-5 w-5 text-white" />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <span className="text-base font-bold tracking-tight text-zinc-100">AgeixAI</span>
            <span className="text-[10px] font-medium tracking-[0.2em] text-emerald-400 uppercase">SOC</span>
          </div>
          <span className="text-[10px] tracking-wider text-zinc-500 uppercase">Unified Cyber Ops</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {navItems.map((group) => (
          <div key={group.section} className="mb-6">
            <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
              {group.section}
            </div>
            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive = pathname === item.href || (item.href !== "/command-center" && pathname.startsWith(item.href))
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                      isActive
                        ? "bg-emerald-600/15 text-emerald-400 shadow-sm shadow-emerald-600/10 border border-emerald-700/30"
                        : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200 border border-transparent"
                    )}
                  >
                    <item.icon className={cn("h-4 w-4 flex-shrink-0", isActive ? "text-emerald-400" : "text-zinc-500")} />
                    {item.label}
                    {item.href === "/command-center" && (
                      <span className="ml-auto flex h-5 w-5 items-center justify-center rounded-full bg-red-600/20 text-[10px] font-bold text-red-400">
                        7
                      </span>
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* System Status */}
      <div className="border-t border-zinc-800/60 px-4 py-3">
        <div className="flex items-center gap-3 rounded-lg bg-zinc-900/60 px-3 py-2.5">
          <div className="flex h-2 w-2">
            <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-emerald-500 opacity-75" />
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium text-zinc-300">All Systems Nominal</span>
            <span className="text-[10px] text-zinc-500">6/6 Agents Online</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
