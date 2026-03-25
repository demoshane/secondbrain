import { useState, useEffect, useCallback } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { getAPI } from '@/lib/utils'
import { useNoteContext } from '@/contexts/NoteContext'
import { useUIContext } from '@/contexts/UIContext'
import { ActionItemList } from './ActionItemList'
import type { ActionItem, Note } from '@/types'

export function ActionsPage() {
  const { openNote } = useNoteContext()
  const { setCurrentView } = useUIContext()
  const [actions, setActions] = useState<ActionItem[]>([])
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'done'>('open')
  const [people, setPeople] = useState<Note[]>([])
  const [assigneeFilter, setAssigneeFilter] = useState<string>('all')
  const [pendingDelete, setPendingDelete] = useState<ActionItem | null>(null)
  const [deleting, setDeleting] = useState(false)

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
      .then(d => setPeople((d.notes ?? []).filter((n: Note) => n.type === 'person')))
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

  const setDueDate = async (action: ActionItem, date: string | null) => {
    await fetch(`${getAPI()}/actions/${action.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ due_date: date }),
    })
    loadActions()
  }

  const confirmDelete = async () => {
    if (!pendingDelete || deleting) return
    setDeleting(true)
    try {
      await fetch(`${getAPI()}/actions/${pendingDelete.id}`, { method: 'DELETE' })
      setPendingDelete(null)
      loadActions()
    } finally {
      setDeleting(false)
    }
  }

  const openSourceNote = useCallback(async (notePath: string) => {
    await openNote(notePath)
    setCurrentView('notes')
  }, [openNote, setCurrentView])

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
        <ActionItemList
          actions={actions}
          people={people}
          onToggle={toggleDone}
          onAssign={assignTo}
          onSetDueDate={setDueDate}
          onDelete={setPendingDelete}
          showSourceLink={true}
          onOpenNote={openSourceNote}
        />
      </div>

      <Dialog open={!!pendingDelete} onOpenChange={v => !v && setPendingDelete(null)}>
        <DialogContent data-testid="delete-action-modal">
          <DialogHeader>
            <DialogTitle>Delete action item?</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">This cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setPendingDelete(null)}>
                Keep
              </Button>
              <Button
                variant="destructive"
                disabled={deleting}
                onClick={confirmDelete}
                data-testid="delete-action-confirm"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
