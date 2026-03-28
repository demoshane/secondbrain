import { cn } from "@/lib/utils"

const importanceColorMap: Record<string, { bg: string; text: string; label: string }> = {
  high:   { bg: "bg-[#3b1010]", text: "text-[#f87171]", label: "HIGH" },
  medium: { bg: "bg-[#2d1f0a]", text: "text-[#fbbf24]", label: "MED" },
  low:    { bg: "bg-[#1a1a1a]", text: "text-[#64748b]", label: "LOW" },
}

interface ImportanceBadgeProps {
  importance?: string
  className?: string
}

function ImportanceBadge({ importance, className }: ImportanceBadgeProps) {
  const level = importance && importanceColorMap[importance] ? importance : "medium"
  const { bg, text, label } = importanceColorMap[level]
  return (
    <span className={cn("inline-flex items-center rounded px-1.5 py-0.5 font-mono font-semibold", bg, text, className)}>
      {label}
    </span>
  )
}

export { ImportanceBadge, importanceColorMap }
