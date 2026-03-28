import { type LucideIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  icon: LucideIcon
  heading: string
  body: string
  actionLabel?: string
  onAction?: () => void
  className?: string
}

function EmptyState({ icon: Icon, heading, body, actionLabel, onAction, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 py-12 px-6 text-center", className)}>
      <Icon className="h-12 w-12 text-muted-foreground" />
      <div className="flex flex-col gap-1">
        <p className="text-lg font-semibold text-foreground">{heading}</p>
        <p className="text-sm text-muted-foreground">{body}</p>
      </div>
      {actionLabel && onAction && (
        <Button variant="default" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}

export { EmptyState }
