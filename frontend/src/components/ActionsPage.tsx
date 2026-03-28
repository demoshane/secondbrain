import { useState, useEffect, useCallback } from 'react'
import { CheckCircle2, Filter, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { EmptyState } from '@/components/ui/empty-state'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { getAPI } from '@/lib/utils'
import { useNoteContext } from '@/contexts/NoteContext'
import { useUIContext } from '@/contexts/UIContext'
import type { ActionItem, Note } from '@/types'

export function ActionsPage() {
  const { openNote } = useNoteContext()
  const { setCurrentView } = useUIContext()
  const [actions, setActions] = useState<ActionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'done'>('open')
  const [people, setPeople] = useState<Note[]>([])
  const [assigneeFilter, setAssigneeFilter] = useState<string>('all')
  const [pendingDelete, setPendingDelete] = useState<ActionItem | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadActions = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'all') params.set('done', statusFilter === 'done' ? '1' : '0')
      if (assigneeFilter !== 'all') params.set('assignee', assigneeFilter)
      const res = await fetch(`${getAPI()}/actions?${params}`)
      const data = await res.json()
      setActions(data.actions ?? [])
    } catch {
      // keep previous data
    } finally {
      setLoading(false)
    }
  }, [statusFilter, assigneeFilter])

  useEffect(() => { loadActions() }, [loadActions])

  useEffect(() => {
    fetch(`${getAPI()}/notes`)
      .then(r => r.json())
      .then(d => setPeople((d.notes ?? []).filter((n: Note) => n.type === 'person')))
      .catch(() => {})
  }, [])

  const toggleDone = async (id: number) => {
    const action = actions.find(a => a.id === id)
    if (!action) return
    await fetch(`${getAPI()}/actions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ done: !action.done }),
    })
    loadActions()
  }

  const handleDelete = (id: number) => {
    const action = actions.find(a => a.id === id)
    if (action) setPendingDelete(action)
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

  const clearFilters = () => {
    setStatusFilter('all')
    setAssigneeFilter('all')
  }

  const hasFilter = statusFilter !== 'open' || assigneeFilter !== 'all'

  // Derive empty state type
  const isEmpty = actions.length === 0
  const isFilteredEmpty = isEmpty && hasFilter

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-background" data-testid="actions-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Action Items</h2>
        <Button variant="default" size="sm">
          <Plus className="h-4 w-4 mr-1" />
          New Action
        </Button>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex items-center gap-1">
          {(['open', 'done', 'all'] as const).map(f => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={
                statusFilter === f
                  ? 'px-3 py-1 text-sm rounded bg-secondary text-foreground font-medium'
                  : 'px-3 py-1 text-sm rounded text-muted-foreground hover:bg-secondary/50 transition-colors'
              }
            >
              {f === 'open' ? 'Open' : f === 'done' ? 'Done' : 'All'}
            </button>
          ))}
        </div>
        {people.length > 0 && (
          <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
            <SelectTrigger className="w-40 h-8" data-testid="assignee-filter">
              <SelectValue placeholder="All assignees" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All assignees</SelectItem>
              {people.map(p => <SelectItem key={p.path} value={p.path}>{p.title}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Content */}
      {loading ? (
        <SkeletonList count={5} rowHeight="h-10" />
      ) : isFilteredEmpty ? (
        <EmptyState
          icon={Filter}
          heading="No matching items"
          body="Try clearing your filters."
          actionLabel="Clear filters"
          onAction={clearFilters}
        />
      ) : isEmpty ? (
        <EmptyState
          icon={CheckCircle2}
          heading="All clear"
          body="No open action items. You're on top of things."
        />
      ) : (
        <div className="flex flex-col">
          {actions.map(item => (
            <ActionItemRow
              key={item.id}
              item={item}
              onToggle={toggleDone}
              onDelete={handleDelete}
              showSource={true}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        title="Remove this action item?"
        description="It will be deleted permanently."
        confirmLabel={deleting ? 'Deleting...' : 'Remove Item'}
        cancelLabel="Go Back"
        variant="destructive"
      />
    </div>
  )
}
