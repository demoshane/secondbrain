import { useState } from "react"
import { Trash2, Pencil } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"
import { type ActionItem } from "@/types"

interface ActionItemRowProps {
  item: ActionItem
  onToggle: (id: number) => void
  onDelete: (id: number) => void
  onAssign?: (id: number, path: string | null) => void
  onSetDue?: (id: number, date: string | null) => void
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
  onSetDue,
  showSource: _showSource,
  className,
}: ActionItemRowProps) {
  const [editingDue, setEditingDue] = useState(false)
  const [dueInput, setDueInput] = useState(item.due_date ?? '')

  const handleConfirmDue = () => {
    if (onSetDue) {
      onSetDue(item.id, dueInput || null)
    }
    setEditingDue(false)
  }

  const handleCancelDue = () => {
    setDueInput(item.due_date ?? '')
    setEditingDue(false)
  }

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
        {editingDue ? (
          <div className="flex items-center gap-1 mt-1">
            <input
              type="date"
              value={dueInput}
              onChange={e => setDueInput(e.target.value)}
              className="text-xs bg-input border border-border rounded px-1.5 py-0.5 text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              onKeyDown={e => {
                if (e.key === 'Enter') handleConfirmDue()
                if (e.key === 'Escape') handleCancelDue()
              }}
              autoFocus
            />
            <button
              type="button"
              onClick={handleConfirmDue}
              className="text-xs px-1.5 py-0.5 text-green-400 hover:text-green-300"
              aria-label="Confirm due date"
            >
              ✓
            </button>
            <button
              type="button"
              onClick={handleCancelDue}
              className="text-xs px-1.5 py-0.5 text-muted-foreground hover:text-foreground"
              aria-label="Cancel"
            >
              ✕
            </button>
          </div>
        ) : item.due_date ? (
          <button
            type="button"
            onClick={() => { setDueInput(item.due_date ?? ''); setEditingDue(true) }}
            className={cn(
              "group/due flex items-center gap-1 text-xs mt-0.5",
              isOverdue(item.due_date) && !item.done
                ? "text-red-400"
                : "text-muted-foreground"
            )}
          >
            <span>Due: {item.due_date}</span>
            <Pencil className="h-3 w-3 opacity-0 group-hover/due:opacity-100 transition-opacity" />
          </button>
        ) : onSetDue ? (
          <button
            type="button"
            onClick={() => { setDueInput(''); setEditingDue(true) }}
            className="text-xs mt-0.5 text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
          >
            Set deadline
          </button>
        ) : null}
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
