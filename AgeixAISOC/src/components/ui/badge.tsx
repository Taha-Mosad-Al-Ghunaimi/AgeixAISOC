import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-emerald-600/20 text-emerald-400",
        secondary: "border-zinc-700 bg-zinc-800 text-zinc-300",
        destructive: "border-transparent bg-red-600/20 text-red-400",
        warning: "border-transparent bg-amber-600/20 text-amber-400",
        info: "border-transparent bg-blue-600/20 text-blue-400",
        outline: "text-zinc-400 border-zinc-700",
        critical: "border-transparent bg-red-600/30 text-red-300 shadow-[0_0_10px_rgba(220,38,38,0.15)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
