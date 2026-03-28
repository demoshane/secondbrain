import { X } from "lucide-react"
import { cn } from "@/lib/utils"

interface TagBadgeProps {
  tag: string
  onClick?: () => void
  onRemove?: () => void
  className?: string
}

function TagBadge({ tag, onClick, onRemove, className }: TagBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full bg-primary/20 text-primary px-2 py-0.5 text-xs cursor-default",
        onClick && "cursor-pointer hover:bg-primary/30",
        className
      )}
      onClick={onClick}
    >
      <span className="text-primary/70">#</span>{tag}
      {onRemove && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onRemove() }}
          className="ml-0.5 rounded-full hover:bg-primary/20 p-0.5 text-primary/70 hover:text-primary"
          aria-label={`Remove tag ${tag}`}
        >
          <X className="h-2.5 w-2.5" />
        </button>
      )}
    </span>
  )
}

export { TagBadge }
