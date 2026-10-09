"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { tenants } from "@/lib/mock-data"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Bell, Search, ChevronDown, Activity } from "lucide-react"

const notificationCount = 12

export function Header() {
  const [currentTenant, setCurrentTenant] = useState(tenants[0])

  return (
    <header className="fixed left-64 right-0 top-0 z-30 flex h-16 items-center justify-between border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-xl px-6">
      {/* Left: Tenant + Search */}
      <div className="flex items-center gap-6">
        <Select value={currentTenant.id} onValueChange={(v) => setCurrentTenant(tenants.find((t) => t.id === v) ?? tenants[0])}>
          <SelectTrigger className="w-52 h-10 border-zinc-700/60 bg-zinc-900/60">
            <SelectValue>
              <div className="flex items-center gap-2">
                <Activity className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-sm font-medium text-zinc-200">{currentTenant.name}</span>
              </div>
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {tenants.map((t) => (
              <SelectItem key={t.id} value={t.id}>
                <div className="flex items-center justify-between w-full">
                  <span>{t.name}</span>
                  <Badge variant={t.plan === "Enterprise" ? "default" : t.plan === "Pro" ? "info" : "secondary"} className="ml-6 text-[10px] px-1.5 py-0">
                    {t.plan}
                  </Badge>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            placeholder="Search alerts, hosts, IoCs..."
            className="h-10 w-80 rounded-lg border border-zinc-700/60 bg-zinc-900/60 pl-10 pr-4 text-sm text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-600/50"
          />
        </div>
      </div>

      {/* Right: Actions + Profile */}
      <div className="flex items-center gap-4">
        {/* Plan Badge */}
        <Badge variant="default" className="gap-1.5 px-3 py-1.5 text-xs">
          <div className="flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
          {currentTenant.plan} Plan
        </Badge>

        {/* Notifications */}
        <button className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-700/60 bg-zinc-900/60 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-all">
          <Bell className="h-4 w-4" />
          {notificationCount > 0 && (
            <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold text-white shadow-lg shadow-red-600/30">
              {notificationCount}
            </span>
          )}
        </button>

        {/* Profile */}
        <div className="flex items-center gap-3 pl-2 border-l border-zinc-800">
          <div className="flex flex-col items-end">
            <span className="text-sm font-medium text-zinc-200">Analyst-01</span>
            <span className="text-[10px] text-zinc-500">Senior SOC</span>
          </div>
          <Avatar className="h-9 w-9 border border-zinc-700/60">
            <AvatarFallback className="bg-gradient-to-br from-emerald-700 to-zinc-800 text-zinc-200 text-xs font-bold">
              A1
            </AvatarFallback>
          </Avatar>
        </div>
      </div>
    </header>
  )
}
