import { useState, useEffect, useCallback, useRef } from 'react'
import { WikiMarkdown } from './WikiMarkdown'
import { Briefcase, Plus, Trash2, Link, Pencil, X } from 'lucide-react'
import { cn, getAPI, encodePath } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EmptyState } from '@/components/ui/empty-state'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { ActionDetailModal } from '@/components/ui/action-detail-modal'
import { NoteTypeBadge } from '@/components/ui/note-type-badge'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { NewEntityModal } from './NewEntityModal'
import { DeleteEntityModal } from './DeleteEntityModal'
import { FileUploadModal } from './FileUploadModal'
import { AttachmentsSection } from '@/components/ui/attachments-section'
import { toast } from 'sonner'
import type { ProjectSummary, ActionItem, MeetingSummary } from '@/types'

type LinkedMeeting = { path: string; title: string; meeting_date: string }
type LinkedNote = { path: string; title: string }

function timeAgo(dateStr: string): string {
  if (!dateStr) return '—'
  const ms = Date.now() - new Date(dateStr).getTime()
  if (isNaN(ms)) return '—'
  const mins = Math.floor(ms / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export function ProjectsPage() {
  const { setCurrentView } = useUIContext()
  const { openNote } = useNoteContext()

  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [showNewEntity, setShowNewEntity] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showDeleteEntity, setShowDeleteEntity] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ name: string; path: string } | null>(null)
  const [projectDetail, setProjectDetail] = useState<{
    body: string
    title: string
    updated_at: string
    status: string
    linked_meetings: LinkedMeeting[]
  } | null>(null)
  const [actions, setActions] = useState<ActionItem[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [detailPeople, setDetailPeople] = useState<LinkedNote[]>([])
  const [connections, setConnections] = useState<LinkedNote[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  // Add action UI state
  const [showAddAction, setShowAddAction] = useState(false)
  const [newActionText, setNewActionText] = useState('')
  const [detailAction, setDetailAction] = useState<ActionItem | null>(null)

  // Inline body editing
  const [editingBody, setEditingBody] = useState<string | null>(null)
  const [savingBody, setSavingBody] = useState(false)

  // Attachments
  const [showUpload, setShowUpload] = useState(false)
  const [attachRefreshTick, setAttachRefreshTick] = useState(0)

  // Link meeting UI state
  const [showLinkMeeting, setShowLinkMeeting] = useState(false)
  const [availableMeetings, setAvailableMeetings] = useState<MeetingSummary[]>([])
  const [selectedMeetingToLink, setSelectedMeetingToLink] = useState<string>('')
  const [linkingMeeting, setLinkingMeeting] = useState(false)

  // Tags editing
  const [newTagInput, setNewTagInput] = useState('')
  const [showAddTag, setShowAddTag] = useState(false)
  const [savingTags, setSavingTags] = useState(false)

  // People editing
  const [showAddPerson, setShowAddPerson] = useState(false)
  const [availablePeople, setAvailablePeople] = useState<LinkedNote[]>([])
  const [selectedPersonPath, setSelectedPersonPath] = useState('')
  const [savingPeople, setSavingPeople] = useState(false)

  // Tag autocomplete
  const [allTags, setAllTags] = useState<string[]>([])

  // Related notes (connections)
  const [showLinkNote, setShowLinkNote] = useState(false)
  const [noteSearchQuery, setNoteSearchQuery] = useState('')
  const [noteSearchResults, setNoteSearchResults] = useState<LinkedNote[]>([])
  const noteSearchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadProjects = () => {
    setLoading(true)
    fetch(`${getAPI()}/projects`)
      .then(r => r.json())
      .then(d => setProjects(d.projects ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjectDetail = (path: string) => {
    setDetailLoading(true)
    setTags([])
    setDetailPeople([])
    setConnections([])
    const enc = encodePath(path)
    Promise.all([
      fetch(`${getAPI()}/projects/${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json()),
      fetch(`${getAPI()}/actions?note_path=${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/notes/${enc}`).then(r => r.json()),
    ]).then(([detail, meta, acts, noteData]) => {
      setProjectDetail({
        body: detail.body ?? '',
        title: detail.title ?? '',
        updated_at: detail.updated_at ?? '',
        status: detail.status ?? 'active',
        linked_meetings: detail.linked_meetings ?? [],
      })
      setActions(acts.actions ?? [])
      setTags(noteData.tags ?? [])
      setDetailPeople(meta.people ?? [])
      setConnections(meta.connections ?? [])
    }).catch(() => {})
      .finally(() => setDetailLoading(false))
  }

  useEffect(() => {
    if (!selectedPath) return
    setEditingBody(null)
    setAttachRefreshTick(0)
    setShowAddTag(false)
    setNewTagInput('')
    setShowAddPerson(false)
    setSelectedPersonPath('')
    setShowLinkNote(false)
    setNoteSearchQuery('')
    setNoteSearchResults([])
    loadProjectDetail(selectedPath)
  }, [selectedPath])

  const reloadActions = () => {
    if (!selectedPath) return
    const enc = encodePath(selectedPath)
    fetch(`${getAPI()}/actions?note_path=${enc}`)
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
      setProjectDetail(prev => prev ? { ...prev, body: editingBody } : prev)
      setEditingBody(null)
      toast.success('Project notes saved')
    } catch {
      toast.error('Failed to save. Try again.')
    } finally {
      setSavingBody(false)
    }
  }

  // ── Tags ────────────────────────────────────────────────────────────────────

  const saveTags = async (newTags: string[]) => {
    if (!selectedPath) return
    setSavingTags(true)
    try {
      const enc = encodePath(selectedPath)
      const res = await fetch(`${getAPI()}/notes/${enc}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags: newTags }),
      })
      if (!res.ok) throw new Error()
      setTags(newTags)
    } catch {
      toast.error('Failed to save tags')
    } finally {
      setSavingTags(false)
    }
  }

  const handleShowAddTag = () => {
    if (allTags.length === 0) {
      fetch(`${getAPI()}/tags`)
        .then(r => r.json())
        .then(d => setAllTags(d.tags ?? []))
        .catch(() => {})
    }
    setShowAddTag(true)
  }

  const handleAddTag = async () => {
    const tag = newTagInput.trim().toLowerCase().replace(/\s+/g, '-')
    if (!tag || tags.includes(tag)) { setNewTagInput(''); setShowAddTag(false); return }
    await saveTags([...tags, tag])
    setNewTagInput('')
    setShowAddTag(false)
  }

  const handleRemoveTag = (tag: string) => {
    saveTags(tags.filter(t => t !== tag))
  }

  // ── People ──────────────────────────────────────────────────────────────────

  const handleShowAddPerson = () => {
    if (availablePeople.length === 0) {
      fetch(`${getAPI()}/persons?limit=200`)
        .then(r => r.json())
        .then(d => setAvailablePeople((d.people ?? []).map((p: any) => ({ path: p.path, title: p.title }))))
        .catch(() => {})
    }
    setShowAddPerson(true)
  }

  const savePeople = async (newPeople: LinkedNote[]) => {
    if (!selectedPath) return
    setSavingPeople(true)
    try {
      const enc = encodePath(selectedPath)
      const res = await fetch(`${getAPI()}/notes/${enc}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ people: newPeople.map(p => p.path) }),
      })
      if (!res.ok) throw new Error()
      setDetailPeople(newPeople)
    } catch {
      toast.error('Failed to save people')
    } finally {
      setSavingPeople(false)
    }
  }

  const handleAddPerson = (person: LinkedNote) => {
    if (detailPeople.some(p => p.path === person.path)) { setShowAddPerson(false); return }
    savePeople([...detailPeople, person])
    setShowAddPerson(false)
  }

  const handleRemovePerson = (path: string) => {
    savePeople(detailPeople.filter(p => p.path !== path))
  }

  // ── Related Notes ───────────────────────────────────────────────────────────

  const handleNoteSearch = useCallback((q: string) => {
    setNoteSearchQuery(q)
    if (noteSearchTimer.current) clearTimeout(noteSearchTimer.current)
    if (!q.trim()) { setNoteSearchResults([]); return }
    noteSearchTimer.current = setTimeout(async () => {
      try {
        const res = await fetch(`${getAPI()}/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, limit: 10 }),
        })
        const data = await res.json()
        const results: LinkedNote[] = (data.results ?? [])
          .filter((r: any) => r.path !== selectedPath)
          .map((r: any) => ({ path: r.path, title: r.title || r.path }))
        setNoteSearchResults(results)
      } catch {
        setNoteSearchResults([])
      }
    }, 300)
  }, [selectedPath])

  const handleLinkNote = async (note: LinkedNote) => {
    if (!selectedPath) return
    if (connections.some(c => c.path === note.path)) { setShowLinkNote(false); setNoteSearchQuery(''); setNoteSearchResults([]); return }
    try {
      const res = await fetch(`${getAPI()}/relationships`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_path: selectedPath, target_path: note.path, rel_type: 'connection' }),
      })
      if (!res.ok) throw new Error()
      setConnections(prev => [...prev, note])
      toast.success('Note linked')
    } catch {
      toast.error('Failed to link note')
    }
    setShowLinkNote(false)
    setNoteSearchQuery('')
    setNoteSearchResults([])
  }

  const handleUnlinkNote = async (notePath: string) => {
    if (!selectedPath) return
    try {
      const res = await fetch(`${getAPI()}/relationships`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_path: selectedPath, target_path: notePath }),
      })
      if (!res.ok) throw new Error()
      setConnections(prev => prev.filter(c => c.path !== notePath))
    } catch {
      toast.error('Failed to unlink note')
    }
  }

  // ── Meetings ────────────────────────────────────────────────────────────────

  const handleShowLinkMeeting = () => {
    fetch(`${getAPI()}/meetings?limit=50`)
      .then(r => r.json())
      .then(d => setAvailableMeetings(d.meetings ?? []))
      .catch(() => toast.error('Failed to load meetings'))
    setSelectedMeetingToLink('')
    setShowLinkMeeting(true)
  }

  const handleLinkMeeting = async () => {
    if (!selectedPath || !selectedMeetingToLink) return
    setLinkingMeeting(true)
    const enc = encodePath(selectedPath)
    try {
      const res = await fetch(`${getAPI()}/projects/${enc}/meetings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meeting_path: selectedMeetingToLink }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        toast.error(err.error ?? 'Failed to link meeting')
        return
      }
      toast.success('Meeting linked')
      setShowLinkMeeting(false)
      loadProjectDetail(selectedPath)
    } catch {
      toast.error('Something went wrong. Try again.')
    } finally {
      setLinkingMeeting(false)
    }
  }

  const handleUnlinkMeeting = async (meetingPath: string) => {
    if (!selectedPath) return
    const projEnc = encodePath(selectedPath)
    const mtgEnc = encodePath(meetingPath)
    try {
      const res = await fetch(`${getAPI()}/projects/${projEnc}/meetings/${mtgEnc}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      setProjectDetail(prev => prev
        ? { ...prev, linked_meetings: prev.linked_meetings.filter(m => m.path !== meetingPath) }
        : prev
      )
    } catch {
      toast.error('Failed to unlink meeting')
    }
  }

  // ────────────────────────────────────────────────────────────────────────────

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-400 bg-green-500/10'
      case 'paused': return 'text-amber-400 bg-amber-500/10'
      case 'completed': return 'text-muted-foreground bg-muted/50'
      default: return 'text-muted-foreground bg-muted/50'
    }
  }

  const filtered = projects.filter(p =>
    p.title.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="flex flex-1 overflow-hidden" data-testid="projects-page">
      {/* List column */}
      <div className="w-80 border-r border-border bg-card flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <span className="text-sm font-semibold text-foreground">Projects</span>
          <Button
            variant="default"
            size="sm"
            onClick={() => setShowNewEntity(true)}
            data-testid="new-project-button"
          >
            <Plus className="h-4 w-4 mr-1" />
            New Project
          </Button>
        </div>
        <div className="px-3 py-2 border-b border-border shrink-0">
          <input
            placeholder="Filter by title..."
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
              icon={Briefcase}
              heading="No projects yet"
              body="Start tracking a project."
              actionLabel="New Project"
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
                  data-testid="project-row"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground truncate">{p.title}</span>
                    {p.open_actions > 0 && (
                      <span className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground text-xs w-5 h-5 shrink-0 ml-2">
                        {p.open_actions}
                      </span>
                    )}
                  </div>
                  {p.updated_at && (
                    <div className="text-xs text-muted-foreground mt-0.5">{p.updated_at}</div>
                  )}
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
              icon={Briefcase}
              heading="Select a project"
              body="Choose a project to see status, actions, and linked meetings."
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
                <div className="flex flex-col gap-1">
                  <h1 className="text-xl font-semibold text-foreground">{projectDetail?.title ?? ''}</h1>
                  {projectDetail?.status && (
                    <span className={cn(
                      'self-start inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                      getStatusColor(projectDetail.status)
                    )}>
                      {projectDetail.status.charAt(0).toUpperCase() + projectDetail.status.slice(1)}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {editingBody === null && (
                    <Button size="sm" variant="outline" onClick={() => setEditingBody(projectDetail?.body ?? '')}>
                      <Pencil className="h-4 w-4 mr-1" />
                      Edit
                    </Button>
                  )}
                  <Button size="sm" variant="outline" onClick={handleOpenInNotes}>
                    Open in Notes
                  </Button>
                </div>
              </div>
              <div className="flex items-center gap-4 mt-4" data-testid="stat-tiles">
                <div className="flex-1 rounded-lg border border-border bg-card p-3 text-center">
                  <div className="text-lg font-semibold text-foreground">{connections.length}</div>
                  <div className="text-xs text-muted-foreground">Related Notes</div>
                </div>
                <div className="flex-1 rounded-lg border border-border bg-card p-3 text-center">
                  <div className="text-lg font-semibold text-foreground">{actions.filter(a => !a.done).length}</div>
                  <div className="text-xs text-muted-foreground">Open Actions</div>
                </div>
                <div className="flex-1 rounded-lg border border-border bg-card p-3 text-center">
                  <div className="text-lg font-semibold text-foreground">{projectDetail?.linked_meetings.length ?? 0}</div>
                  <div className="text-xs text-muted-foreground">Linked Meetings</div>
                </div>
                <div className="flex-1 rounded-lg border border-border bg-card p-3 text-center">
                  <div className="text-lg font-semibold text-foreground">{timeAgo(projectDetail?.updated_at ?? '')}</div>
                  <div className="text-xs text-muted-foreground">Last Updated</div>
                </div>
              </div>
            </div>

            <div className="flex-1 divide-y divide-border">
              {/* Actions */}
              <CollapsibleSection
                title="Actions"
                count={actions.filter(a => !a.done).length}
                sectionId={`projects-actions-${selectedPath}`}
                defaultOpen={true}
              >
                <div data-testid="project-actions-section">
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
                          onOpen={setDetailAction}
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

              {/* Linked Meetings */}
              <CollapsibleSection
                title="Linked Meetings"
                count={projectDetail?.linked_meetings.length ?? 0}
                sectionId={`projects-meetings-${selectedPath}`}
                defaultOpen={true}
              >
                <div className="px-4 py-3">
                  {(projectDetail?.linked_meetings.length ?? 0) === 0 ? (
                    <p className="text-sm text-muted-foreground mb-3">No linked meetings</p>
                  ) : (
                    <ul className="space-y-1.5 mb-3">
                      {projectDetail!.linked_meetings.map(m => (
                        <li key={m.path} className="flex items-center gap-2 text-sm group">
                          <NoteTypeBadge type="meeting" />
                          <span className="text-foreground flex-1">{m.title}</span>
                          {m.meeting_date && (
                            <span className="text-xs text-muted-foreground">{m.meeting_date}</span>
                          )}
                          <button
                            type="button"
                            onClick={() => handleUnlinkMeeting(m.path)}
                            className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity ml-1"
                            title="Unlink meeting"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}

                  {!showLinkMeeting ? (
                    <Button variant="outline" size="sm" onClick={handleShowLinkMeeting}>
                      <Link className="h-3.5 w-3.5 mr-1.5" />
                      Link Meeting
                    </Button>
                  ) : (
                    <div className="flex items-center gap-2 mt-1">
                      <select
                        value={selectedMeetingToLink}
                        onChange={e => setSelectedMeetingToLink(e.target.value)}
                        className="flex-1 rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground outline-none focus:ring-1 focus:ring-ring"
                      >
                        <option value="">Select a meeting...</option>
                        {availableMeetings.map(m => (
                          <option key={m.path} value={m.path}>{m.title}</option>
                        ))}
                      </select>
                      <Button size="sm" onClick={handleLinkMeeting} disabled={!selectedMeetingToLink || linkingMeeting}>
                        Link
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setShowLinkMeeting(false)}>
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              </CollapsibleSection>

              {/* Tags */}
              <CollapsibleSection
                title="Tags"
                count={tags.length}
                sectionId={`projects-tags-${selectedPath}`}
                defaultOpen={tags.length > 0}
              >
                <div className="px-4 py-3">
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {tags.map(tag => (
                      <span key={tag} className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground group">
                        #{tag}
                        <button
                          type="button"
                          onClick={() => handleRemoveTag(tag)}
                          disabled={savingTags}
                          className="opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                  {showAddTag ? (
                    <div className="flex gap-2 mt-1">
                      <input
                        autoFocus
                        list="project-tag-suggestions"
                        className="flex-1 text-sm bg-input border border-border rounded px-2 py-1 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                        placeholder="tag-name"
                        value={newTagInput}
                        onChange={e => setNewTagInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') handleAddTag(); if (e.key === 'Escape') { setShowAddTag(false); setNewTagInput('') } }}
                      />
                      <datalist id="project-tag-suggestions">
                        {allTags.filter(t => !tags.includes(t)).map(t => (
                          <option key={t} value={t} />
                        ))}
                      </datalist>
                      <button type="button" onClick={handleAddTag} disabled={savingTags} className="text-xs px-2 py-1 bg-primary text-primary-foreground rounded disabled:opacity-50">Add</button>
                      <button type="button" onClick={() => { setShowAddTag(false); setNewTagInput('') }} className="text-xs px-2 py-1 text-muted-foreground">Cancel</button>
                    </div>
                  ) : (
                    <button type="button" onClick={handleShowAddTag} className="text-xs text-muted-foreground hover:text-foreground">
                      + Add tag
                    </button>
                  )}
                </div>
              </CollapsibleSection>

              {/* People */}
              <CollapsibleSection
                title="People"
                count={detailPeople.length}
                sectionId={`projects-people-${selectedPath}`}
                defaultOpen={detailPeople.length > 0}
              >
                <div className="px-4 py-3">
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {detailPeople.map(p => (
                      <span key={p.path} className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2 py-0.5 text-xs font-medium group">
                        {p.title}
                        <button
                          type="button"
                          onClick={() => handleRemovePerson(p.path)}
                          disabled={savingPeople}
                          className="opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                  {showAddPerson ? (
                    <div className="mt-1 flex flex-col gap-1">
                      <div className="flex gap-2">
                        <select
                          autoFocus
                          value={selectedPersonPath}
                          onChange={e => setSelectedPersonPath(e.target.value)}
                          className="flex-1 rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground outline-none focus:ring-1 focus:ring-ring"
                        >
                          <option value="">Select a person...</option>
                          {availablePeople
                            .filter(p => !detailPeople.some(dp => dp.path === p.path))
                            .map(p => (
                              <option key={p.path} value={p.path}>{p.title}</option>
                            ))
                          }
                        </select>
                        <Button
                          size="sm"
                          disabled={!selectedPersonPath || savingPeople}
                          onClick={() => {
                            const person = availablePeople.find(p => p.path === selectedPersonPath)
                            if (person) handleAddPerson(person)
                            setSelectedPersonPath('')
                          }}
                        >
                          Link
                        </Button>
                      </div>
                      <button type="button" onClick={() => { setShowAddPerson(false); setSelectedPersonPath('') }} className="text-xs text-muted-foreground">Cancel</button>
                    </div>
                  ) : (
                    <button type="button" onClick={handleShowAddPerson} className="text-xs text-muted-foreground hover:text-foreground">
                      + Link person
                    </button>
                  )}
                </div>
              </CollapsibleSection>

              {/* Notes body */}
              <CollapsibleSection
                title="Notes"
                count={1}
                sectionId={`projects-notes-${selectedPath}`}
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
                    {projectDetail?.body
                      ? <WikiMarkdown>{projectDetail.body}</WikiMarkdown>
                      : <p className="text-sm text-muted-foreground">No project notes yet.</p>
                    }
                  </div>
                )}
              </CollapsibleSection>

              {/* Related Notes (manual connections) */}
              <CollapsibleSection
                title="Related Notes"
                count={connections.length}
                sectionId={`projects-related-${selectedPath}`}
                defaultOpen={connections.length > 0}
              >
                <div data-testid="project-backlinks-section" className="px-4 py-3">
                  {connections.length > 0 && (
                    <ul className="space-y-1.5 mb-3">
                      {connections.map(c => (
                        <li key={c.path} className="flex items-center gap-2 text-sm group">
                          <button
                            type="button"
                            onClick={() => { openNote(c.path); setCurrentView('notes') }}
                            className="text-foreground flex-1 text-left hover:underline"
                          >
                            {c.title || c.path}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleUnlinkNote(c.path)}
                            className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity"
                            title="Unlink note"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  {showLinkNote ? (
                    <div className="mt-1">
                      <input
                        autoFocus
                        className="w-full text-sm bg-input border border-border rounded px-2 py-1 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring mb-1"
                        placeholder="Search notes…"
                        value={noteSearchQuery}
                        onChange={e => handleNoteSearch(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Escape') { setShowLinkNote(false); setNoteSearchQuery(''); setNoteSearchResults([]) } }}
                      />
                      {noteSearchResults.length > 0 && (
                        <ul className="border border-border rounded bg-card divide-y divide-border max-h-40 overflow-y-auto mb-1">
                          {noteSearchResults.map(r => (
                            <li key={r.path}>
                              <button
                                type="button"
                                onClick={() => handleLinkNote(r)}
                                className="w-full text-left px-3 py-1.5 text-sm text-foreground hover:bg-secondary transition-colors"
                              >
                                {r.title || r.path}
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                      <button type="button" onClick={() => { setShowLinkNote(false); setNoteSearchQuery(''); setNoteSearchResults([]) }} className="text-xs text-muted-foreground">Cancel</button>
                    </div>
                  ) : (
                    <button type="button" onClick={() => setShowLinkNote(true)} className="text-xs text-muted-foreground hover:text-foreground">
                      {connections.length === 0 ? 'No related notes — ' : ''} + Link note
                    </button>
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
                  if (!projectDetail) return
                  setDeleteTarget({ name: projectDetail.title, path: selectedPath })
                  setShowDeleteConfirm(true)
                }}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Project
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

      <NewEntityModal
        open={showNewEntity}
        onClose={() => setShowNewEntity(false)}
        entityType="projects"
        onCreated={loadProjects}
      />

      {deleteTarget && (
        <>
          <ConfirmDialog
            open={showDeleteConfirm}
            onClose={() => setShowDeleteConfirm(false)}
            onConfirm={() => {
              setShowDeleteConfirm(false)
              setShowDeleteEntity(true)
            }}
            title={`Delete '${deleteTarget.name}'?`}
            description="This cannot be undone."
            confirmLabel="Delete Project"
            cancelLabel="Keep Project"
            variant="destructive"
          />
          <DeleteEntityModal
            open={showDeleteEntity}
            onClose={() => { setShowDeleteEntity(false); setDeleteTarget(null) }}
            entityType="projects"
            entityName={deleteTarget.name}
            entityPath={deleteTarget.path}
            onDeleted={() => {
              loadProjects()
              if (selectedPath === deleteTarget.path) setSelectedPath(null)
            }}
          />
        </>
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
    </div>
  )
}
