import { useState, useEffect, useCallback } from 'react'
import { CheckCircle2, ChevronDown, ChevronRight, Filter, Plus, CalendarDays, List } from 'lucide-react'
import { InfoTip } from '@/components/ui/info-tip'
import { Button } from '@/components/ui/button'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { ActionDetailModal } from '@/components/ui/action-detail-modal'
import { ActionsCalendar } from '@/components/ui/actions-calendar'
import { EmptyState } from '@/components/ui/empty-state'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { getAPI } from '@/lib/utils'
import { toast } from 'sonner'
import type { ActionItem, PersonSummary } from '@/types'

type ActiveTab = 'list' | 'calendar'

function groupBySource(items: ActionItem[]): Map<string, ActionItem[]> {
  const map = new Map<string, ActionItem[]>()
  for (const item of items) {
    const key = item.note_path
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(item)
  }
  return map
}

function extractTitle(notePath: string | null): string {
  if (!notePath) return 'Unassigned'
  const segments = notePath.split('/')
  const filename = segments[segments.length - 1] ?? notePath
  const noExt = filename.endsWith('.md') ? filename.slice(0, -3) : filename
  const spaced = noExt.replace(/[-_]/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export function ActionsPage() {
  const [actions, setActions] = useState<ActionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'done'>('open')
  const [people, setPeople] = useState<PersonSummary[]>([])
  const [assigneeFilter, setAssigneeFilter] = useState<string>('all')
  const [pendingDelete, setPendingDelete] = useState<ActionItem | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [allCollapsed, setAllCollapsed] = useState(false)
  const [groupCollapsed, setGroupCollapsed] = useState<Map<string, boolean>>(new Map())
  const [showNewAction, setShowNewAction] = useState(false)
  const [newActionText, setNewActionText] = useState('')
  const [newActionDate, setNewActionDate] = useState('')
  const [newActionAssignee, setNewActionAssignee] = useState('')
  const [savingNew, setSavingNew] = useState(false)
  const [activeTab, setActiveTab] = useState<ActiveTab>('list')
  const [calendarActions, setCalendarActions] = useState<ActionItem[]>([])
  const [detailAction, setDetailAction] = useState<ActionItem | null>(null)

  const loadCalendarActions = useCallback(async () => {
    try {
      const res = await fetch(`${getAPI()}/actions?limit=200`)
      const data = await res.json()
      setCalendarActions(data.actions ?? [])
    } catch {}
  }, [])

  useEffect(() => {
    if (activeTab === 'calendar') loadCalendarActions()
  }, [activeTab, loadCalendarActions])

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
    fetch(`${getAPI()}/persons`)
      .then(r => r.json())
      .then(d => setPeople(d.people ?? []))
      .catch(() => {})
  }, [])

  // When allCollapsed changes, reset per-group state to match
  useEffect(() => {
    setGroupCollapsed(new Map())
  }, [allCollapsed])

  const updateAction = useCallback(async (
    id: number,
    patch: Partial<Pick<ActionItem, 'done' | 'due_date' | 'assignee_path'>>
  ) => {
    await fetch(`${getAPI()}/actions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    loadActions()
    loadCalendarActions()
  }, [loadActions, loadCalendarActions])

  const toggleDone = (id: number) => {
    const action = actions.find(a => a.id === id) ?? calendarActions.find(a => a.id === id)
    if (!action) return
    updateAction(id, { done: !action.done })
  }

  const handleSetDue = (id: number, date: string | null) => {
    updateAction(id, { due_date: date })
  }

  const handleAssign = (id: number, path: string | null) => {
    updateAction(id, { assignee_path: path })
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

  const openNewAction = (date?: string) => {
    setNewActionDate(date ?? '')
    setShowNewAction(true)
  }

  const handleNewActionSave = async () => {
    const text = newActionText.trim()
    if (!text) return
    setSavingNew(true)
    try {
      const body: Record<string, string | null> = { text }
      if (newActionDate) body.due_date = newActionDate
      if (newActionAssignee) body.assignee_path = newActionAssignee
      const res = await fetch(`${getAPI()}/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error()
      toast.success('Action added')
      setNewActionText('')
      setNewActionDate('')
      setNewActionAssignee('')
      setShowNewAction(false)
      loadActions()
      loadCalendarActions()
    } catch {
      toast.error('Failed to add action. Try again.')
    } finally {
      setSavingNew(false)
    }
  }

  const clearFilters = () => {
    setStatusFilter('all')
    setAssigneeFilter('all')
  }

  const toggleGroup = (key: string) => {
    setGroupCollapsed(prev => {
      const next = new Map(prev)
      const current = next.has(key) ? next.get(key)! : allCollapsed
      next.set(key, !current)
      return next
    })
  }

  const isGroupCollapsed = (key: string): boolean => {
    if (groupCollapsed.has(key)) return groupCollapsed.get(key)!
    return allCollapsed
  }

  const hasFilter = statusFilter !== 'open' || assigneeFilter !== 'all'
  const isEmpty = actions.length === 0
  const isFilteredEmpty = isEmpty && hasFilter

  const grouped = groupBySource(actions)

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-background" data-testid="actions-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold flex items-center">Action Items<InfoTip text="Tasks extracted from your notes. Filter by assignee, source note, or completion status. Toggle done to mark complete." /></h2>
          {/* List / Calendar tab toggle */}
          <div className="flex items-center gap-0.5 border border-border rounded-md p-0.5">
            <button
              onClick={() => setActiveTab('list')}
              className={
                activeTab === 'list'
                  ? 'flex items-center gap-1.5 px-2.5 py-1 text-xs rounded bg-secondary text-foreground font-medium'
                  : 'flex items-center gap-1.5 px-2.5 py-1 text-xs rounded text-muted-foreground hover:text-foreground transition-colors'
              }
            >
              <List className="h-3.5 w-3.5" />
              List
            </button>
            <button
              onClick={() => setActiveTab('calendar')}
              className={
                activeTab === 'calendar'
                  ? 'flex items-center gap-1.5 px-2.5 py-1 text-xs rounded bg-secondary text-foreground font-medium'
                  : 'flex items-center gap-1.5 px-2.5 py-1 text-xs rounded text-muted-foreground hover:text-foreground transition-colors'
              }
            >
              <CalendarDays className="h-3.5 w-3.5" />
              Calendar
            </button>
          </div>
        </div>
        <Button variant="default" size="sm" onClick={() => openNewAction()}>
          <Plus className="h-4 w-4 mr-1" />
          New Action
        </Button>
      </div>

      {/* Calendar tab */}
      {activeTab === 'calendar' && (
        <div className="flex flex-col" style={{ height: 'calc(100vh - 180px)' }}>
          {/* New action form — rendered inline so it's always visible */}
          {showNewAction && (
            <div className="flex items-center gap-2 mb-3 p-3 rounded-lg border border-border bg-card flex-wrap shrink-0">
              <input
                autoFocus
                value={newActionText}
                onChange={e => setNewActionText(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleNewActionSave()
                  if (e.key === 'Escape') setShowNewAction(false)
                }}
                placeholder="What needs to be done?"
                className="flex-1 min-w-40 rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
              />
              <input
                type="date"
                value={newActionDate}
                onChange={e => setNewActionDate(e.target.value)}
                className="text-sm bg-input border border-input rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                aria-label="Deadline"
              />
              {people.length > 0 && (
                <select
                  value={newActionAssignee}
                  onChange={e => setNewActionAssignee(e.target.value)}
                  className="text-sm bg-input border border-input rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  aria-label="Assignee"
                >
                  <option value="">No assignee</option>
                  {people.map(p => (
                    <option key={p.path} value={p.path}>{p.title}</option>
                  ))}
                </select>
              )}
              <Button size="sm" onClick={handleNewActionSave} disabled={savingNew || !newActionText.trim()}>
                {savingNew ? 'Saving…' : 'Add'}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowNewAction(false)}>Cancel</Button>
            </div>
          )}
          <div className="flex-1 min-h-0">
            <ActionsCalendar
              actions={calendarActions}
              onToggle={toggleDone}
              onAddAction={date => openNewAction(date)}
              onOpen={setDetailAction}
            />
          </div>
        </div>
      )}

      {/* List tab */}
      {activeTab === 'list' && (
        <>
          {/* New action form */}
          {showNewAction && (
            <div className="flex items-center gap-2 mb-4 p-3 rounded-lg border border-border bg-card flex-wrap">
              <input
                autoFocus
                value={newActionText}
                onChange={e => setNewActionText(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleNewActionSave()
                  if (e.key === 'Escape') setShowNewAction(false)
                }}
                placeholder="What needs to be done?"
                className="flex-1 min-w-40 rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
              />
              <input
                type="date"
                value={newActionDate}
                onChange={e => setNewActionDate(e.target.value)}
                className="text-sm bg-input border border-input rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                aria-label="Deadline"
              />
              {people.length > 0 && (
                <select
                  value={newActionAssignee}
                  onChange={e => setNewActionAssignee(e.target.value)}
                  className="text-sm bg-input border border-input rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  aria-label="Assignee"
                >
                  <option value="">No assignee</option>
                  {people.map(p => (
                    <option key={p.path} value={p.path}>{p.title}</option>
                  ))}
                </select>
              )}
              <Button size="sm" onClick={handleNewActionSave} disabled={savingNew || !newActionText.trim()}>
                {savingNew ? 'Saving…' : 'Add'}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowNewAction(false)}>Cancel</Button>
            </div>
          )}

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
                  {people.map(p => (
                    <SelectItem key={p.path} value={p.path}>{p.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

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
            <>
              {/* Sort label + Collapse toggle */}
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-muted-foreground">Sort by: Source Note</span>
                <button
                  onClick={() => setAllCollapsed(prev => !prev)}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  {allCollapsed ? (
                    <ChevronRight className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                  {allCollapsed ? 'Expand All' : 'Collapse All'}
                </button>
              </div>

              {/* Grouped sections */}
              <div className="flex flex-col gap-2">
                {Array.from(grouped.entries()).map(([notePath, items]) => {
                  const collapsed = isGroupCollapsed(notePath)
                  const title = extractTitle(notePath)
                  return (
                    <div key={notePath} className="rounded-md border border-border overflow-hidden">
                      {/* Group header */}
                      <button
                        type="button"
                        onClick={() => toggleGroup(notePath)}
                        className="w-full flex items-center justify-between px-3 py-2 bg-secondary/30 hover:bg-secondary/50 transition-colors text-left"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          {collapsed ? (
                            <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                          )}
                          <span className="text-sm font-medium text-foreground truncate">{title}</span>
                        </div>
                        <span className="text-xs text-muted-foreground shrink-0 ml-2">
                          {items.length} {items.length === 1 ? 'item' : 'items'}
                        </span>
                      </button>

                      {/* Group body */}
                      {!collapsed && (
                        <div className="flex flex-col">
                          {items.map(item => (
                            <ActionItemRow
                              key={item.id}
                              item={item}
                              onToggle={toggleDone}
                              onDelete={handleDelete}
                              onOpen={setDetailAction}
                              onSetDue={handleSetDue}
                              onAssign={handleAssign}
                              people={people}
                              showSource={false}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </>
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

      <ActionDetailModal
        open={!!detailAction}
        action={detailAction}
        onClose={() => setDetailAction(null)}
        onSaved={updated => {
          setActions(prev => prev.map(a => a.id === updated.id ? updated : a))
          setCalendarActions(prev => prev.map(a => a.id === updated.id ? updated : a))
          setDetailAction(null)
        }}
      />
    </div>
  )
}
