import * as React from "react"
import { cn } from "@/lib/utils"

interface HealthScoreGaugeProps {
  score: number
  className?: string
}

function HealthScoreGauge({ score, className }: HealthScoreGaugeProps) {
  const colorClass =
    score >= 80
      ? "text-green-500"
      : score >= 50
      ? "text-amber-400"
      : "text-red-500"

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      <span className={cn("text-[32px] font-semibold leading-none", colorClass)}>
        {score}
      </span>
      <span className="text-xs text-muted-foreground">Brain Health</span>
    </div>
  )
}

export { HealthScoreGauge }
