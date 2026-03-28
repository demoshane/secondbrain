import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const noteTypeColorMap: Record<string, string> = {
  design: 'bg-[#1e3a5f] text-[#60a5fa]',
  research: 'bg-[#2d1f5e] text-[#a78bfa]',
  meeting: 'bg-[#1a2f1a] text-[#4ade80]',
  project: 'bg-[#2f1f0e] text-[#fb923c]',
  idea: 'bg-[#1f2a1a] text-[#86efac]',
  strategy: 'bg-[#1a1f3a] text-[#818cf8]',
  people: 'bg-[#2a1f1f] text-[#f87171]',
  person: 'bg-[#2a1f1f] text-[#f87171]',
  link: 'bg-[#1a2a2a] text-[#2dd4bf]',
}

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  noteType?: string
}

function Badge({ className, variant, noteType, ...props }: BadgeProps) {
  if (noteType) {
    const colorClass = noteTypeColorMap[noteType.toLowerCase()] ?? 'bg-secondary text-[#94a3b8]'
    return (
      <div
        className={cn(
          "inline-flex items-center rounded-md border-transparent px-2.5 py-0.5 text-xs font-semibold",
          colorClass,
          className
        )}
        {...props}
      />
    )
  }
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants, noteTypeColorMap }
