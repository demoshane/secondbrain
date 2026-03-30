import { useState } from "react"
import { Trash2, Pencil, User } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { type ActionItem } from "@/types"

interface PersonOption {
  path: string
  title: string
}

interface ActionItemRowProps {
  item: ActionItem
  onToggle: (id: number) => void
  onDelete: (id: number) => void
  onOpen?: (item: ActionItem) => void
  onAssign?: (id: number, path: string | null) => void
  onSetDue?: (id: number, date: string | null) => void
  people?: PersonOption[]
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
  onOpen,
  onSetDue,
  onAssign,
  people = [],
  showSource: _showSource,
  className,
}: ActionItemRowProps) {
  const [editingDue, setEditingDue] = useState(false)
  const [dueInput, setDueInput] = useState(item.due_date ?? '')
  const [editingAssignee, setEditingAssignee] = useState(false)

  const handleConfirmDue = () => {
    if (onSetDue) onSetDue(item.id, dueInput || null)
    setEditingDue(false)
  }

  const handleCancelDue = () => {
    setDueInput(item.due_date ?? '')
    setEditingDue(false)
  }

  const assigneeName = item.assignee_path
    ? (people.find(p => p.path === item.assignee_path)?.title
        ?? item.assignee_path.split('/').pop()?.replace('.md', '')
        ?? 'Assigned')
    : null

  const handleAssignSelect = (value: string) => {
    if (onAssign) onAssign(item.id, value === 'none' ? null : value)
    setEditingAssignee(false)
  }

  return (
    <div
      data-testid="action-item"
      className={cn(
        "group flex items-start gap-2 px-3 py-2 hover:bg-secondary/30 transition-colors",
        className
      )}
    >
      <Checkbox
        checked={item.done}
        onCheckedChange={() => onToggle(item.id)}
        className="h-5 w-5 mt-0.5 shrink-0"
      />
      <div className="flex-1 min-w-0">
        <button
          type="button"
          onClick={() => onOpen?.(item)}
          className={cn(
            "text-sm text-left w-full",
            onOpen ? "hover:underline cursor-pointer" : "cursor-default",
            item.done ? "line-through text-muted-foreground" : "text-foreground"
          )}
        >
          {item.text}
        </button>

        {/* Metadata row: deadline + assignee */}
        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
          {/* Due date */}
          {editingDue ? (
            <div className="flex items-center gap-1">
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
              >✓</button>
              <button
                type="button"
                onClick={handleCancelDue}
                className="text-xs px-1.5 py-0.5 text-muted-foreground hover:text-foreground"
                aria-label="Cancel"
              >✕</button>
            </div>
          ) : item.due_date ? (
            <button
              type="button"
              onClick={() => { setDueInput(item.due_date ?? ''); setEditingDue(true) }}
              className={cn(
                "group/due flex items-center gap-1 text-xs",
                isOverdue(item.due_date) && !item.done ? "text-red-400" : "text-muted-foreground"
              )}
            >
              <span>Due: {item.due_date}</span>
              <Pencil className="h-3 w-3 opacity-0 group-hover/due:opacity-100 transition-opacity" />
            </button>
          ) : onSetDue ? (
            <button
              type="button"
              onClick={() => { setDueInput(''); setEditingDue(true) }}
              className="text-xs text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
            >
              Set deadline
            </button>
          ) : null}

          {/* Assignee */}
          {editingAssignee ? (
            <Select
              value={item.assignee_path ?? 'none'}
              defaultOpen
              onValueChange={handleAssignSelect}
              onOpenChange={open => { if (!open) setEditingAssignee(false) }}
            >
              <SelectTrigger className="h-6 text-xs px-1.5 w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Unassigned</SelectItem>
                {people.map(p => (
                  <SelectItem key={p.path} value={p.path}>{p.title}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : assigneeName ? (
            <button
              type="button"
              onClick={() => onAssign && setEditingAssignee(true)}
              className="group/assignee flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <User className="h-3 w-3" />
              <span>{assigneeName}</span>
              {onAssign && (
                <Pencil className="h-3 w-3 opacity-0 group-hover/assignee:opacity-100 transition-opacity" />
              )}
            </button>
          ) : onAssign && people.length > 0 ? (
            <button
              type="button"
              onClick={() => setEditingAssignee(true)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <User className="h-3 w-3" />
              <span>Assign</span>
            </button>
          ) : null}
        </div>
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
