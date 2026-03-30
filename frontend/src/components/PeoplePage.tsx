import { useState, useEffect, useRef } from 'react'
import { WikiMarkdown } from './WikiMarkdown'
import { Users, Plus, Trash2, Pencil, Unlink } from 'lucide-react'
import { cn, getAPI, encodePath } from '@/lib/utils'

function AvatarInitials({ name, size = 'lg' }: { name: string; size?: 'sm' | 'lg' }) {
  const words = name.trim().split(/\s+/)
  let initials: string
  if (words.length === 1) {
    initials = words[0].slice(0, 2).toUpperCase()
  } else {
    initials = (words[0][0] + words[words.length - 1][0]).toUpperCase()
  }
  const sizeClass = size === 'lg' ? 'w-16 h-16 text-xl' : 'w-8 h-8 text-xs'
  return (
    <div className={cn('rounded-full bg-primary/20 text-primary font-semibold flex items-center justify-center shrink-0', sizeClass)}>
      {initials}
    </div>
  )
}
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EmptyState } from '@/components/ui/empty-state'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { ActionDetailModal } from '@/components/ui/action-detail-modal'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { NewEntityModal } from './NewEntityModal'
import { DeleteEntityModal } from './DeleteEntityModal'
import { FileUploadModal } from './FileUploadModal'
import { AttachmentsSection } from '@/components/ui/attachments-section'
import { toast } from 'sonner'
import type { PersonSummary, ActionItem } from '@/types'

export function PeoplePage() {
  const { setCurrentView } = useUIContext()
  const { openNote } = useNoteContext()

  const [people, setPeople] = useState<PersonSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [selectedPerson, setSelectedPerson] = useState<PersonSummary | null>(null)
  const [personNote, setPersonNote] = useState<{ body: string; title: string } | null>(null)
  const [meetings, setMeetings] = useState<{ path: string; title: string }[]>([])
  const [backlinks, setBacklinks] = useState<{ path: string; title: string }[]>([])
  const [actions, setActions] = useState<ActionItem[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [showNewEntity, setShowNewEntity] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ name: string; path: string } | null>(null)
  const [showDeleteEntity, setShowDeleteEntity] = useState(false)
  const [connections, setConnections] = useState<{ path: string; title: string }[]>([])
  const [connQuery, setConnQuery] = useState('')
  const [connResults, setConnResults] = useState<{ path: string; title: string }[]>([])
  const [showConnDropdown, setShowConnDropdown] = useState(false)
  const connSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const connInputRef = useRef<HTMLInputElement>(null)
  const [connDropdownRect, setConnDropdownRect] = useState<DOMRect | null>(null)
  const [showAddAction, setShowAddAction] = useState(false)
  const [newActionText, setNewActionText] = useState('')
  const [actionsTab, setActionsTab] = useState<'open' | 'done'>('open')
  const [detailAction, setDetailAction] = useState<ActionItem | null>(null)
  const [editingBody, setEditingBody] = useState<string | null>(null)
  const [savingBody, setSavingBody] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [attachRefreshTick, setAttachRefreshTick] = useState(0)

  const loadPeople = () => {
    setLoading(true)
    fetch(`${getAPI()}/persons`)
      .then(r => r.json())
      .then(d => setPeople(d.people ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadPeople()
  }, [])

  useEffect(() => {
    if (!selectedPath) return
    setDetailLoading(true)
    setEditingBody(null)
    setAttachRefreshTick(0)
    const person = people.find(p => p.path === selectedPath) ?? null
    setSelectedPerson(person)
    const enc = encodePath(selectedPath)
    Promise.all([
      fetch(`${getAPI()}/notes/${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json()),
      fetch(`${getAPI()}/actions?assignee=${enc}`).then(r => r.json()),
    ]).then(([note, meta, acts]) => {
      setPersonNote({ body: note.body ?? '', title: note.title ?? '' })
      const metaMeetings: { path: string; title: string }[] = meta.meetings ?? []
      const bl: { path: string; title: string }[] = meta.backlinks ?? []
      if (metaMeetings.length > 0) {
        setMeetings(metaMeetings)
        setBacklinks(bl)
      } else {
        setMeetings(bl.filter(b => (b as { path: string; title: string; type?: string }).type === 'meeting'))
        setBacklinks(bl.filter(b => (b as { path: string; title: string; type?: string }).type !== 'meeting'))
      }
      setConnections(meta.connections ?? [])
      setActions(acts.actions ?? [])
    }).catch(() => {})
      .finally(() => setDetailLoading(false))
  }, [selectedPath, people])

  const reloadActions = () => {
    if (!selectedPath) return
    const enc = encodePath(selectedPath)
    fetch(`${getAPI()}/actions?assignee=${enc}`)
      .then(r => r.json())
      .then(d => setActions(d.actions ?? []))
      .catch(() => {})
  }

  const handleToggleAction = async (id: number) => {
    const action = actions.find(a => a.id === id)
    if (!action) return
    try {
      await fetch(`${getAPI()}/actions/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done: !action.done }),
      })
      toast.success(action.done ? 'Marked open' : 'Marked complete')
      reloadActions()
    } catch {
      toast.error('Something went wrong. Try again.')
    }
  }

  const handleDeleteAction = async (id: number) => {
    try {
      await fetch(`${getAPI()}/actions/${id}`, { method: 'DELETE' })
      toast.success('Action item removed')
      reloadActions()
    } catch {
      toast.error('Something went wrong. Try again.')
    }
  }

  const handleSetDue = async (id: number, date: string | null) => {
    try {
      await fetch(`${getAPI()}/actions/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ due_date: date }),
      })
      reloadActions()
    } catch {
      toast.error('Failed to update deadline')
    }
  }

  const handleAddAction = async () => {
    if (!newActionText.trim() || !selectedPath) return
    try {
      await fetch(`${getAPI()}/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: newActionText.trim(), assignee_path: selectedPath }),
      })
      setNewActionText('')
      setShowAddAction(false)
      reloadActions()
    } catch {
      toast.error('Failed to add action')
    }
  }

  async function handleOpenInNotes() {
    if (!selectedPath) return
    await openNote(selectedPath)
    setCurrentView('notes')
  }

  const handleSaveBody = async () => {
    if (editingBody === null || !selectedPath || savingBody) return
    setSavingBody(true)
    try {
      const enc = encodePath(selectedPath)
      const res = await fetch(`${getAPI()}/notes/${enc}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: editingBody }),
      })
      if (!res.ok) throw new Error('Save failed')
      setPersonNote(prev => prev ? { ...prev, body: editingBody } : prev)
      setEditingBody(null)
      toast.success('Person note saved')
    } catch {
      toast.error('Failed to save. Try again.')
    } finally {
      setSavingBody(false)
    }
  }

  const addConnection = async (targetPath: string) => {
    if (!selectedPath) return
    if (connections.some(c => c.path === targetPath)) return
    const enc = encodePath(selectedPath)
    try {
      await fetch(`${getAPI()}/notes/${enc}/connections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: targetPath }),
      })
      setConnQuery('')
      setConnResults([])
      setShowConnDropdown(false)
      const meta = await fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json())
      setConnections(meta.connections ?? [])
    } catch {
      toast.error('Failed to add connection')
    }
  }

  const removeConnection = async (targetPath: string) => {
    if (!selectedPath) return
    const enc = encodePath(selectedPath)
    try {
      await fetch(`${getAPI()}/notes/${enc}/connections`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: targetPath }),
      })
      const meta = await fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json())
      setConnections(meta.connections ?? [])
    } catch {
      toast.error('Failed to remove connection')
    }
  }

  const handleConnQueryChange = (q: string) => {
    setConnQuery(q)
    if (connSearchRef.current) clearTimeout(connSearchRef.current)
    if (!q.trim()) {
      setConnResults([])
      setShowConnDropdown(false)
      return
    }
    if (connInputRef.current) setConnDropdownRect(connInputRef.current.getBoundingClientRect())
    connSearchRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${getAPI()}/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, limit: 5 }),
        })
        const data = await res.json()
        const filtered = (data.results ?? []).filter((r: { path: string }) =>
          r.path !== selectedPath && !connections.some(c => c.path === r.path)
        )
        setConnResults(filtered)
        setShowConnDropdown(filtered.length > 0)
      } catch {
        setConnResults([])
      }
    }, 250)
  }

  const filtered = people.filter(p =>
    p.title.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="flex flex-1 overflow-hidden" data-testid="people-page">
      {/* List column */}
      <div className="w-80 border-r border-border bg-card flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <span className="text-sm font-semibold text-foreground">People</span>
          <Button
            variant="default"
            size="sm"
            onClick={() => setShowNewEntity(true)}
            data-testid="new-person-button"
          >
            <Plus className="h-4 w-4 mr-1" />
            New Person
          </Button>
        </div>
        <div className="px-3 py-2 border-b border-border shrink-0">
          <input
            placeholder="Filter by name..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="w-full rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <ScrollArea className="flex-1">
          {loading ? (
            <SkeletonList count={6} rowHeight="h-12" />
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={Users}
              heading="No people yet"
              body="Add people to your brain to track relationships and interactions."
              actionLabel="New Person"
              onAction={() => setShowNewEntity(true)}
              className="py-8"
            />
          ) : (
            <div>
              {filtered.map(p => (
                <div
                  key={p.path}
                  className={cn(
                    'px-4 py-2.5 cursor-pointer border-b border-border hover:bg-secondary/50 transition-colors',
                    selectedPath === p.path && 'bg-secondary'
                  )}
                  onClick={() => setSelectedPath(p.path)}
                  data-testid="person-row"
                >
                  <div className="flex items-center gap-2.5">
                    <AvatarInitials name={p.title} size="sm" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground truncate">{p.title}</span>
                        {p.open_actions > 0 && (
                          <span className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground text-xs w-5 h-5 shrink-0 ml-2">
                            {p.open_actions}
                          </span>
                        )}
                      </div>
                      {p.org && (
                        <div className="text-xs text-muted-foreground truncate mt-0.5">{p.org}</div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Detail column */}
      <div className="flex-1 bg-background overflow-y-auto">
        {!selectedPath ? (
          <div className="flex h-full items-center justify-center">
            <EmptyState
              icon={Users}
              heading="Select a person"
              body="Choose someone from the list to see their profile and connections."
            />
          </div>
        ) : detailLoading ? (
          <div className="p-6">
            <SkeletonList count={4} rowHeight="h-8" />
          </div>
        ) : (
          <div className="flex flex-col h-full">
            <div className="px-6 py-4 border-b border-border shrink-0">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-4">
                  <AvatarInitials name={personNote?.title ?? selectedPerson?.title ?? ''} size="lg" />
                  <div>
                    <h1 className="text-xl font-semibold text-foreground">{personNote?.title ?? ''}</h1>
                    {selectedPerson?.org && (
                      <p className="text-sm text-muted-foreground mt-0.5">{selectedPerson.org}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {editingBody === null && (
                    <Button size="sm" variant="outline" onClick={() => setEditingBody(personNote?.body ?? '')}>
                      <Pencil className="h-4 w-4 mr-1" />
                      Edit
                    </Button>
                  )}
                  <Button size="sm" variant="outline" onClick={handleOpenInNotes}>
                    Open in Notes
                  </Button>
                </div>
              </div>
            </div>

            <div className="flex-1 divide-y divide-border">
              <CollapsibleSection
                title="Profile & Context"
                count={1}
                sectionId={`people-insight-${selectedPath}`}
                defaultOpen={true}
              >
                {editingBody !== null ? (
                  <div className="px-4 py-3 flex flex-col gap-3">
                    <textarea
                      autoFocus
                      className="w-full min-h-[300px] font-mono text-sm bg-input border border-border rounded px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-y"
                      value={editingBody}
                      onChange={e => setEditingBody(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); handleSaveBody() }
                        if (e.key === 'Escape') { e.preventDefault(); setEditingBody(null) }
                      }}
                    />
                    <div className="flex items-center gap-2">
                      <Button size="sm" onClick={handleSaveBody} disabled={savingBody}>
                        {savingBody ? 'Saving…' : 'Save'}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingBody(null)}>Cancel</Button>
                      <span className="text-xs text-muted-foreground">Cmd+Enter to save · Esc to cancel</span>
                    </div>
                  </div>
                ) : (
                  <div className="px-4 py-3 prose prose-sm prose-invert max-w-none leading-relaxed">
                    {personNote?.body
                      ? <WikiMarkdown>{personNote.body}</WikiMarkdown>
                      : <p className="text-sm text-muted-foreground">No profile written yet.</p>
                    }
                  </div>
                )}
              </CollapsibleSection>

              <CollapsibleSection
                title="Actions"
                count={actions.filter(a => !a.done).length}
                sectionId={`people-actions-${selectedPath}`}
                defaultOpen={true}
              >
                <div data-testid="actions-section">
                  {/* Tab toggle */}
                  <div className="flex items-center gap-0.5 px-3 pt-1 pb-2">
                    {(['open', 'done'] as const).map(tab => (
                      <button
                        key={tab}
                        onClick={() => setActionsTab(tab)}
                        className={
                          actionsTab === tab
                            ? 'px-2.5 py-0.5 text-xs rounded bg-secondary text-foreground font-medium'
                            : 'px-2.5 py-0.5 text-xs rounded text-muted-foreground hover:bg-secondary/50 transition-colors'
                        }
                      >
                        {tab === 'open' ? `Open (${actions.filter(a => !a.done).length})` : `Done (${actions.filter(a => a.done).length})`}
                      </button>
                    ))}
                  </div>

                  {actionsTab === 'open' ? (
                    actions.filter(a => !a.done).length === 0 ? (
                      <p className="px-4 py-3 text-sm text-muted-foreground">No open actions</p>
                    ) : (
                      <div>
                        {actions.filter(a => !a.done).map(action => (
                          <ActionItemRow
                            key={action.id}
                            item={action}
                            onToggle={handleToggleAction}
                            onDelete={handleDeleteAction}
                            onOpen={setDetailAction}
                            onSetDue={handleSetDue}
                          />
                        ))}
                      </div>
                    )
                  ) : (
                    actions.filter(a => a.done).length === 0 ? (
                      <p className="px-4 py-3 text-sm text-muted-foreground">No completed actions</p>
                    ) : (
                      <div>
                        {actions.filter(a => a.done).map(action => (
                          <ActionItemRow
                            key={action.id}
                            item={action}
                            onToggle={handleToggleAction}
                            onDelete={handleDeleteAction}
                            onOpen={setDetailAction}
                            onSetDue={handleSetDue}
                          />
                        ))}
                      </div>
                    )
                  )}

                  {actionsTab === 'open' && (
                    <div className="px-3 py-2">
                      {showAddAction ? (
                        <div className="flex gap-2">
                          <input
                            autoFocus
                            className="flex-1 text-sm bg-input border border-border rounded px-2 py-1 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                            placeholder="New action item…"
                            value={newActionText}
                            onChange={e => setNewActionText(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') handleAddAction(); if (e.key === 'Escape') setShowAddAction(false) }}
                          />
                          <button type="button" onClick={handleAddAction} className="text-xs px-2 py-1 bg-primary text-primary-foreground rounded">Add</button>
                          <button type="button" onClick={() => setShowAddAction(false)} className="text-xs px-2 py-1 text-muted-foreground">Cancel</button>
                        </div>
                      ) : (
                        <button type="button" onClick={() => setShowAddAction(true)} className="text-xs text-muted-foreground hover:text-foreground">+ Add action</button>
                      )}
                    </div>
                  )}
                </div>
              </CollapsibleSection>

              <CollapsibleSection
                title="Related Notes"
                count={backlinks.length + meetings.length + connections.length}
                sectionId={`people-related-${selectedPath}`}
                defaultOpen={true}
              >
                <div data-testid="backlinks-section">
                  {meetings.length === 0 && backlinks.length === 0 && connections.length === 0 ? (
                    <p className="px-4 py-3 text-sm text-muted-foreground">No related notes</p>
                  ) : (
                    <div>
                      {meetings.map(m => (
                        <div key={m.path} className="flex items-center px-4 py-1.5 hover:bg-secondary/50">
                          <button
                            className="flex-1 text-left text-sm truncate text-muted-foreground hover:text-foreground"
                            onClick={() => { openNote(m.path); setCurrentView('notes') }}
                          >
                            {m.title}
                          </button>
                        </div>
                      ))}
                      {backlinks.map(b => (
                        <div key={b.path} className="flex items-center px-4 py-1.5 hover:bg-secondary/50">
                          <button
                            className="flex-1 text-left text-sm truncate text-muted-foreground hover:text-foreground"
                            onClick={() => { openNote(b.path); setCurrentView('notes') }}
                          >
                            {b.title}
                          </button>
                        </div>
                      ))}
                      {connections.map(c => (
                        <div key={c.path} className="flex items-center group px-4 py-1.5 hover:bg-secondary/50">
                          <button
                            className="flex-1 text-left text-sm truncate text-muted-foreground hover:text-foreground"
                            onClick={() => { openNote(c.path); setCurrentView('notes') }}
                          >
                            {c.title}
                          </button>
                          <button
                            type="button"
                            className="ml-1 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive"
                            onClick={() => removeConnection(c.path)}
                            aria-label="Remove connection"
                          >
                            <Unlink className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="px-4 pb-3">
                  <input
                    ref={connInputRef}
                    type="text"
                    placeholder="+ connect note"
                    value={connQuery}
                    className="w-full text-xs bg-transparent border border-border rounded px-2 py-1 text-muted-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50"
                    onChange={e => handleConnQueryChange(e.target.value)}
                    onBlur={() => setTimeout(() => setShowConnDropdown(false), 150)}
                  />
                  {showConnDropdown && connResults.length > 0 && connDropdownRect && (
                    <div
                      style={{ position: 'fixed', top: connDropdownRect.bottom + 2, left: connDropdownRect.left, width: connDropdownRect.width, zIndex: 9999 }}
                      className="bg-card border border-border rounded shadow-lg max-h-40 overflow-y-auto"
                    >
                      {connResults.map(r => (
                        <button
                          key={r.path}
                          type="button"
                          className="block w-full text-left px-2 py-1.5 text-xs hover:bg-secondary/50 text-foreground truncate"
                          onMouseDown={() => addConnection(r.path)}
                        >
                          {r.title}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </CollapsibleSection>
            </div>

            {/* Attachments */}
            <div className="px-6 py-3 border-t border-border">
              <AttachmentsSection
                notePath={selectedPath}
                refreshTick={attachRefreshTick}
                onUploadClick={() => setShowUpload(true)}
              />
            </div>

            <div className="px-6 py-4 border-t border-border shrink-0">
              <Button
                variant="ghost"
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={() => {
                  if (!selectedPerson) return
                  setDeleteTarget({ name: selectedPerson.title, path: selectedPath })
                  setShowDeleteConfirm(true)
                }}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Person
              </Button>
            </div>
          </div>
        )}
      </div>

      {selectedPath && (
        <FileUploadModal
          open={showUpload}
          onClose={() => setShowUpload(false)}
          onUploaded={() => setAttachRefreshTick(t => t + 1)}
          notePath={selectedPath}
        />
      )}

      <ActionDetailModal
        open={!!detailAction}
        action={detailAction}
        onClose={() => setDetailAction(null)}
        onSaved={updated => {
          setActions(prev => prev.map(a => a.id === updated.id ? updated : a))
          setDetailAction(null)
        }}
      />

      <NewEntityModal
        open={showNewEntity}
        onClose={() => setShowNewEntity(false)}
        entityType="persons"
        onCreated={loadPeople}
      />

      {deleteTarget && (
        <>
          <ConfirmDialog
            open={showDeleteConfirm}
            onClose={() => { setShowDeleteConfirm(false) }}
            onConfirm={() => {
              setShowDeleteConfirm(false)
              setShowDeleteEntity(true)
            }}
            title={`Delete '${deleteTarget.name}'?`}
            description="Their profile note and all associated data will be removed."
            confirmLabel="Delete Person"
            cancelLabel="Keep Person"
            variant="destructive"
          />
          <DeleteEntityModal
            open={showDeleteEntity}
            onClose={() => { setShowDeleteEntity(false); setDeleteTarget(null) }}
            entityType="persons"
            entityName={deleteTarget.name}
            entityPath={deleteTarget.path}
            onDeleted={() => {
              loadPeople()
              if (selectedPath === deleteTarget.path) setSelectedPath(null)
            }}
          />
        </>
      )}
    </div>
  )
}
