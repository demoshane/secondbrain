import { X } from "lucide-react"
import { cn } from "@/lib/utils"

interface PersonBadgeProps {
  name: string
  path?: string
  onRemove?: () => void
  onClick?: () => void
  className?: string
}

function PersonBadge({ name, path: _path, onRemove, onClick, className }: PersonBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground cursor-default",
        onClick && "cursor-pointer hover:bg-secondary/80",
        className
      )}
      onClick={onClick}
    >
      {name}
      {onRemove && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onRemove() }}
          className="ml-0.5 rounded-full hover:bg-muted p-0.5 text-muted-foreground hover:text-foreground"
          aria-label={`Remove ${name}`}
        >
          <X className="h-2.5 w-2.5" />
        </button>
      )}
    </span>
  )
}

export { PersonBadge }
