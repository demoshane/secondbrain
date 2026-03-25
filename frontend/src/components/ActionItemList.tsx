import { ExternalLink, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { ActionItem, Note } from '@/types'

interface ActionItemListProps {
  actions: ActionItem[]
  people: Note[]
  onToggle: (action: ActionItem) => void
  onAssign: (action: ActionItem, assigneePath: string) => void
  onSetDueDate?: (action: ActionItem, date: string | null) => void
  onDelete?: (action: ActionItem) => void
  showSourceLink?: boolean
  onOpenNote?: (notePath: string) => void
}

export function ActionItemList({
  actions,
  people,
  onToggle,
  onAssign,
  onSetDueDate,
  onDelete,
  showSourceLink = false,
  onOpenNote,
}: ActionItemListProps) {
  if (actions.length === 0) {
    return <p className="text-sm text-muted-foreground">No action items</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-8">Done</TableHead>
          <TableHead>Task</TableHead>
          <TableHead>Assignee</TableHead>
          <TableHead>Due</TableHead>
          {showSourceLink && <TableHead className="w-10">Note</TableHead>}
          {onDelete && <TableHead className="w-10"></TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {actions.map(action => (
          <TableRow key={action.id} data-testid="action-row">
            <TableCell>
              <Checkbox
                checked={action.done}
                onCheckedChange={() => onToggle(action)}
                data-testid="action-done-checkbox"
              />
            </TableCell>
            <TableCell
              className={`text-sm${action.done ? ' line-through text-muted-foreground' : ''}${action.note_path ? ' cursor-pointer hover:underline' : ''}`}
              onClick={() => action.note_path && onOpenNote?.(action.note_path)}
            >
              {action.text}
            </TableCell>
            <TableCell>
              <Select value={action.assignee_path ?? 'none'} onValueChange={v => onAssign(action, v)}>
                <SelectTrigger className="h-7 w-36 text-xs">
                  <SelectValue placeholder="Assign…" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Unassigned</SelectItem>
                  {people.map(p => (
                    <SelectItem key={p.path} value={p.path}>{p.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </TableCell>
            <TableCell>
              <input
                type="date"
                className="h-7 w-32 text-xs bg-transparent border border-border rounded px-1.5 text-foreground"
                value={action.due_date ?? ''}
                onChange={e => onSetDueDate?.(action, e.target.value || null)}
              />
            </TableCell>
            {showSourceLink && (
              <TableCell>
                {action.note_path ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    aria-label="Open source note"
                    onClick={() => onOpenNote?.(action.note_path)}
                  >
                    <ExternalLink size={14} />
                  </Button>
                ) : null}
              </TableCell>
            )}
            {onDelete && (
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  aria-label="Delete action item"
                  onClick={() => onDelete(action)}
                >
                  <Trash2 size={14} />
                </Button>
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
