"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { mitreCoverage } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

export function MitreHeatmap() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-zinc-300">MITRE ATT&CK Coverage</CardTitle>
          <span className="text-[11px] text-zinc-500">Overall: 78%</span>
        </div>
      </CardHeader>
      <CardContent>
        <TooltipProvider>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-2">
            {mitreCoverage.map(({ tactic, coverage }) => {
              const intensity =
                coverage >= 85 ? "bg-emerald-600/40 border-emerald-500/40 text-emerald-300" :
                coverage >= 70 ? "bg-emerald-600/25 border-emerald-600/25 text-emerald-400" :
                coverage >= 55 ? "bg-amber-600/20 border-amber-600/25 text-amber-400" :
                "bg-red-600/20 border-red-600/25 text-red-400"

              return (
                <Tooltip key={tactic}>
                  <TooltipTrigger asChild>
                    <div
                      className={cn(
                        "flex flex-col items-center justify-center rounded-lg border px-2 py-2.5 cursor-pointer transition-all hover:scale-105 hover:shadow-lg",
                        intensity
                      )}
                    >
                      <span className="text-[10px] font-bold tracking-tight text-center leading-tight">{tactic}</span>
                      <span className="text-lg font-bold mt-1">{coverage}%</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <p className="text-xs">
                      <strong>{tactic}</strong>: {coverage}% detection coverage
                    </p>
                    <p className="text-[10px] text-zinc-400 mt-1">
                      {coverage >= 85 ? "Strong coverage. Multiple detection rules active." :
                       coverage >= 70 ? "Good coverage. Some gaps exist." :
                       coverage >= 55 ? "Moderate coverage. Gaps identified in detection gap loop." :
                       "Weak coverage. Red team has identified gaps."}
                    </p>
                  </TooltipContent>
                </Tooltip>
              )
            })}
          </div>
        </TooltipProvider>
      </CardContent>
    </Card>
  )
}
