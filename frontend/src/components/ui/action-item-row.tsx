import * as React from "react"
import { Trash2 } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"
import { type ActionItem } from "@/types"

interface ActionItemRowProps {
  item: ActionItem
  onToggle: (id: number) => void
  onDelete: (id: number) => void
  onAssign?: (id: number, path: string | null) => void
  showSource?: boolean
  className?: string
}

function isOverdue(dueDate: string | null): boolean {
  if (!dueDate) return false
  return new Date(dueDate) < new Date()
}

function ActionItemRow({
  item,
  onToggle,
  onDelete,
  showSource: _showSource,
  className,
}: ActionItemRowProps) {
  return (
    <div
      className={cn(
        "group flex items-start gap-2 px-3 py-2 hover:bg-secondary/30 transition-colors",
        className
      )}
    >
      <Checkbox
        id={`action-${item.id}`}
        checked={item.done}
        onCheckedChange={() => onToggle(item.id)}
        className="h-5 w-5 mt-0.5 shrink-0"
      />
      <div className="flex-1 min-w-0">
        <label
          htmlFor={`action-${item.id}`}
          className={cn(
            "text-sm cursor-pointer",
            item.done
              ? "line-through text-muted-foreground"
              : "text-foreground"
          )}
        >
          {item.text}
        </label>
        {item.due_date && (
          <p
            className={cn(
              "text-xs mt-0.5",
              isOverdue(item.due_date) && !item.done
                ? "text-red-400"
                : "text-muted-foreground"
            )}
          >
            Due: {item.due_date}
          </p>
        )}
      </div>
      <button
        type="button"
        onClick={() => onDelete(item.id)}
        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive shrink-0"
        aria-label="Delete action item"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  )
}

export { ActionItemRow }
