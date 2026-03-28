import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Users, Plus, Trash2, Link, Pencil } from 'lucide-react'
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
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { NewEntityModal } from './NewEntityModal'
import { DeleteEntityModal } from './DeleteEntityModal'
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
  const [showLinkNote, setShowLinkNote] = useState(false)
  const [linkNoteSearch, setLinkNoteSearch] = useState('')
  const [allNotes, setAllNotes] = useState<{ path: string; title: string }[]>([])
  const [selectedNoteToLink, setSelectedNoteToLink] = useState('')
  const [linkingNote, setLinkingNote] = useState(false)
  const [showAddAction, setShowAddAction] = useState(false)
  const [newActionText, setNewActionText] = useState('')
  const [editingBody, setEditingBody] = useState<string | null>(null)
  const [savingBody, setSavingBody] = useState(false)

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
        body: JSON.stringify({ text: newActionText.trim(), note_path: selectedPath }),
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

  const handleShowLinkNote = () => {
    fetch(`${getAPI()}/notes?limit=100`)
      .then(r => r.json())
      .then(d => setAllNotes((d.results ?? []).map((n: { path: string; title: string }) => ({ path: n.path, title: n.title }))))
      .catch(() => {})
    setLinkNoteSearch('')
    setSelectedNoteToLink('')
    setShowLinkNote(true)
  }

  const handleLinkNote = async () => {
    if (!selectedPath || !selectedNoteToLink || linkingNote) return
    setLinkingNote(true)
    try {
      const res = await fetch(`${getAPI()}/relationships`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: selectedPath,
          target_path: selectedNoteToLink,
          rel_type: 'manual',
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        toast.error(err.error ?? 'Failed to link note')
        return
      }
      toast.success('Note linked')
      setShowLinkNote(false)
      // Reload person detail to refresh backlinks
      const enc = encodePath(selectedPath)
      const meta = await fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json())
      setBacklinks(meta.backlinks ?? [])
    } catch {
      toast.error('Something went wrong. Try again.')
    } finally {
      setLinkingNote(false)
    }
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
                      ? <Markdown remarkPlugins={[remarkGfm]}>{personNote.body}</Markdown>
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
                  {actions.filter(a => !a.done).length === 0 ? (
                    <p className="px-4 py-3 text-sm text-muted-foreground">No open actions</p>
                  ) : (
                    <div>
                      {actions.filter(a => !a.done).map(action => (
                        <ActionItemRow
                          key={action.id}
                          item={action}
                          onToggle={handleToggleAction}
                          onDelete={handleDeleteAction}
                          onSetDue={handleSetDue}
                        />
                      ))}
                    </div>
                  )}
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
                </div>
              </CollapsibleSection>

              <CollapsibleSection
                title="Related Notes"
                count={backlinks.length + meetings.length}
                sectionId={`people-related-${selectedPath}`}
                defaultOpen={true}
              >
                <div data-testid="backlinks-section" className="px-4 py-3">
                  {meetings.length === 0 && backlinks.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No related notes</p>
                  ) : (
                    <ul className="space-y-1.5">
                      {meetings.map(m => (
                        <li key={m.path} className="text-sm text-foreground">{m.title}</li>
                      ))}
                      {backlinks.map(b => (
                        <li key={b.path} className="text-sm text-foreground">{b.title}</li>
                      ))}
                    </ul>
                  )}
                </div>
                {!showLinkNote ? (
                  <div className="px-4 pb-3">
                    <Button variant="outline" size="sm" onClick={handleShowLinkNote}>
                      <Link className="h-3.5 w-3.5 mr-1.5" />
                      Link Note
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2 px-4 pb-3">
                    <input
                      placeholder="Search notes..."
                      value={linkNoteSearch}
                      onChange={e => setLinkNoteSearch(e.target.value)}
                      className="rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
                    />
                    <div className="flex items-center gap-2">
                      <select
                        value={selectedNoteToLink}
                        onChange={e => setSelectedNoteToLink(e.target.value)}
                        className="flex-1 rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground outline-none focus:ring-1 focus:ring-ring"
                      >
                        <option value="">Select a note...</option>
                        {allNotes
                          .filter(n => !linkNoteSearch || n.title.toLowerCase().includes(linkNoteSearch.toLowerCase()))
                          .map(n => (
                            <option key={n.path} value={n.path}>{n.title}</option>
                          ))}
                      </select>
                      <Button
                        size="sm"
                        onClick={handleLinkNote}
                        disabled={!selectedNoteToLink || linkingNote}
                      >
                        Link
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setShowLinkNote(false)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </CollapsibleSection>
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
