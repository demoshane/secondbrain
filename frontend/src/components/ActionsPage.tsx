import { useState, useEffect, useCallback } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { getAPI } from '@/lib/utils'
import type { ActionItem, Note } from '@/types'

export function ActionsPage() {
  const [actions, setActions] = useState<ActionItem[]>([])
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'done'>('open')
  const [people, setPeople] = useState<Note[]>([])
  const [assigneeFilter, setAssigneeFilter] = useState<string>('all')

  const loadActions = useCallback(async () => {
    const params = new URLSearchParams()
    if (statusFilter !== 'all') params.set('done', statusFilter === 'done' ? '1' : '0')
    if (assigneeFilter !== 'all') params.set('assignee', assigneeFilter)
    const res = await fetch(`${getAPI()}/actions?${params}`)
    const data = await res.json()
    setActions(data.actions ?? [])
  }, [statusFilter, assigneeFilter])

  useEffect(() => { loadActions() }, [loadActions])

  useEffect(() => {
    fetch(`${getAPI()}/notes`)
      .then(r => r.json())
      .then(d => setPeople((d.notes ?? []).filter((n: Note) => n.type === 'people')))
      .catch(() => {})
  }, [])

  const toggleDone = async (action: ActionItem) => {
    await fetch(`${getAPI()}/actions/${action.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ done: !action.done }),
    })
    loadActions()
  }

  const assignTo = async (action: ActionItem, assigneePath: string) => {
    await fetch(`${getAPI()}/actions/${action.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assignee_path: assigneePath === 'none' ? null : assigneePath }),
    })
    loadActions()
  }

  return (
    <div className="flex flex-col h-full p-4" data-testid="actions-page">
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-lg font-semibold">Action Items</h2>
        <Select value={statusFilter} onValueChange={v => setStatusFilter(v as 'all' | 'open' | 'done')}>
          <SelectTrigger className="w-28 h-8" data-testid="status-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="done">Done</SelectItem>
          </SelectContent>
        </Select>
        <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
          <SelectTrigger className="w-40 h-8" data-testid="assignee-filter">
            <SelectValue placeholder="All assignees" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All assignees</SelectItem>
            {people.map(p => <SelectItem key={p.path} value={p.path}>{p.title}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8">Done</TableHead>
              <TableHead>Task</TableHead>
              <TableHead>Assignee</TableHead>
              <TableHead>Due</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {actions.map(action => (
              <TableRow key={action.id} data-testid="action-row">
                <TableCell>
                  <Checkbox
                    checked={action.done}
                    onCheckedChange={() => toggleDone(action)}
                    data-testid="action-done-checkbox"
                  />
                </TableCell>
                <TableCell className="text-sm">{action.text}</TableCell>
                <TableCell>
                  <Select value={action.assignee_path ?? 'none'} onValueChange={v => assignTo(action, v)}>
                    <SelectTrigger className="h-7 w-36 text-xs">
                      <SelectValue placeholder="Assign…" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Unassigned</SelectItem>
                      {people.map(p => <SelectItem key={p.path} value={p.path}>{p.title}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">{action.due_date ?? '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
