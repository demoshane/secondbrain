import { ExternalLink } from 'lucide-react'
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
  showSourceLink?: boolean
  onOpenNote?: (notePath: string) => void
}

export function ActionItemList({
  actions,
  people,
  onToggle,
  onAssign,
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
            <TableCell className={`text-sm${action.done ? ' line-through text-muted-foreground' : ''}`}>
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
            <TableCell className="text-xs text-muted-foreground">{action.due_date ?? '—'}</TableCell>
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
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
