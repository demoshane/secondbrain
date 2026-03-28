import { cn } from "@/lib/utils"

interface HealthScoreGaugeProps {
  score: number
  className?: string
}

function HealthScoreGauge({ score, className }: HealthScoreGaugeProps) {
  const circumference = 2 * Math.PI * 50 // ~314.16
  const strokeDashoffset = circumference * (1 - score / 100)

  const strokeColor =
    score >= 80
      ? "#22c55e" // green-500
      : score >= 50
      ? "#fbbf24" // amber-400
      : "#ef4444" // red-500

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      <svg
        viewBox="0 0 120 120"
        className="w-24 h-24"
        aria-label={`Brain health score: ${score}`}
      >
        {/* Background track */}
        <circle
          cx="60"
          cy="60"
          r="50"
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth="8"
        />
        {/* Foreground arc */}
        <circle
          cx="60"
          cy="60"
          r="50"
          fill="none"
          stroke={strokeColor}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform="rotate(-90 60 60)"
        />
        {/* Centered score number */}
        <text
          x="60"
          y="60"
          textAnchor="middle"
          dominantBaseline="central"
          fontSize="28"
          fontWeight="600"
          fill={strokeColor}
        >
          {score}
        </text>
      </svg>
      <span className="text-xs text-muted-foreground">Brain Health</span>
    </div>
  )
}

export { HealthScoreGauge }
