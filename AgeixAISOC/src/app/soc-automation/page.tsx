"use client"

import { Separator } from "@/components/ui/separator"
import { SocAutomationHub } from "@/components/dashboard/soc-automation-hub"

export default function SocAutomationPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">SOC Automation Hub</h1>
          <p className="text-sm text-zinc-500 mt-1">
            AgeixAI automates Tier 1/2 SOC tasks &middot; AI processes &middot; Human reviews &middot; System executes
          </p>
        </div>
      </div>

      <Separator className="bg-zinc-800/60" />

      <SocAutomationHub />
    </div>
  )
}
