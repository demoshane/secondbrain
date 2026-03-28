import * as React from "react"
import { cn } from "@/lib/utils"

interface SkeletonListProps {
  count?: number
  rowHeight?: string
  className?: string
}

function SkeletonList({ count = 5, rowHeight = "h-10", className }: SkeletonListProps) {
  return (
    <div className={cn("flex flex-col gap-2 p-2", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={cn("bg-muted animate-pulse rounded", rowHeight)}
        />
      ))}
    </div>
  )
}

export { SkeletonList }
