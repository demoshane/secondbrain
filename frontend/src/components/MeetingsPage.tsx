import { useState, useEffect } from 'react'
import { WikiMarkdown } from './WikiMarkdown'
import { Calendar, Plus, Trash2, Pencil, X } from 'lucide-react'

const MONTH_ABBR = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

function formatDateChip(dateStr: string): { month: string; day: string } | null {
  if (!dateStr) return null
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return null
  return {
    month: MONTH_ABBR[d.getMonth()].toUpperCase(),
    day: String(d.getDate()),
  }
}
import { cn, getAPI, encodePath } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EmptyState } from '@/components/ui/empty-state'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { ActionDetailModal } from '@/components/ui/action-detail-modal'
import { PersonBadge } from '@/components/ui/person-badge'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { NewEntityModal } from './NewEntityModal'
import { DeleteEntityModal } from './DeleteEntityModal'
import { PersonAutocomplete } from './PersonAutocomplete'
import { FileUploadModal } from './FileUploadModal'
import { AttachmentsSection } from '@/components/ui/attachments-section'
import { toast } from 'sonner'
import type { MeetingSummary, ActionItem } from '@/types'

export function MeetingsPage() {
  const { setCurrentView } = useUIContext()
  const { openNote } = useNoteContext()

  const [meetings, setMeetings] = useState<MeetingSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [showNewEntity, setShowNewEntity] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showDeleteEntity, setShowDeleteEntity] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ name: string; path: string } | null>(null)
  const [meetingDetail, setMeetingDetail] = useState<{
    body: string
    title: string
    meeting_date: string
    participants: string[]
  } | null>(null)
  const [actions, setActions] = useState<ActionItem[]>([])
  const [detailAction, setDetailAction] = useState<ActionItem | null>(null)
  const [tags, setTags] = useState<string[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [showAddAction, setShowAddAction] = useState(false)
  const [newActionText, setNewActionText] = useState('')
  const [savingAction, setSavingAction] = useState(false)
  const [showAddParticipant, setShowAddParticipant] = useState(false)
  const [editingBody, setEditingBody] = useState<string | null>(null)
  const [savingBody, setSavingBody] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [attachRefreshTick, setAttachRefreshTick] = useState(0)
  const [newTagInput, setNewTagInput] = useState('')
  const [showAddTag, setShowAddTag] = useState(false)
  const [savingTags, setSavingTags] = useState(false)

  const loadMeetings = () => {
    setLoading(true)
    fetch(`${getAPI()}/meetings`)
      .then(r => r.json())
      .then(d => setMeetings(d.meetings ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadMeetings()
  }, [])

  useEffect(() => {
    if (!selectedPath) return
    setDetailLoading(true)
    setEditingBody(null)
    setAttachRefreshTick(0)
    const enc = encodePath(selectedPath)
    Promise.all([
      fetch(`${getAPI()}/meetings/${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/actions?note_path=${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/notes/${enc}`).then(r => r.json()),
    ]).then(([detail, acts, noteData]) => {
      setMeetingDetail({
        body: detail.body ?? '',
        title: detail.title ?? '',
        meeting_date: detail.meeting_date ?? '',
        participants: (detail.participants ?? []).map(
          (p: { name?: string; path?: string } | string) =>
            typeof p === 'string' ? p : (p.name ?? '')
        ).filter(Boolean),
      })
      setActions(acts.actions ?? [])
      setTags(noteData.tags ?? [])
    }).catch(() => {})
      .finally(() => setDetailLoading(false))
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

  const handleAddAction = async () => {
    const text = newActionText.trim()
    if (!text || !selectedPath) return
    setSavingAction(true)
    try {
      const res = await fetch(`${getAPI()}/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, note_path: selectedPath }),
      })
      if (!res.ok) throw new Error()
      toast.success('Action added')
      setNewActionText('')
      setShowAddAction(false)
      reloadActions()
    } catch {
      toast.error('Failed to add action. Try again.')
    } finally {
      setSavingAction(false)
    }
  }

  const handleAddParticipant = async (name: string) => {
    if (!name || !selectedPath || !meetingDetail) return
    try {
      const enc = encodePath(selectedPath)
      const updatedPeople = [...meetingDetail.participants, name]
      const res = await fetch(`${getAPI()}/notes/${enc}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ people: updatedPeople }),
      })
      if (!res.ok) throw new Error()
      toast.success('Participant added')
      setShowAddParticipant(false)
      setMeetingDetail(prev => prev ? { ...prev, participants: updatedPeople } : prev)
    } catch {
      toast.error('Failed to add participant. Try again.')
    }
  }

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
      setMeetingDetail(prev => prev ? { ...prev, body: editingBody } : prev)
      setEditingBody(null)
      toast.success('Meeting notes saved')
    } catch {
      toast.error('Failed to save. Try again.')
    } finally {
      setSavingBody(false)
    }
  }

  const filtered = meetings.filter(m =>
    m.title.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="flex flex-1 overflow-hidden" data-testid="meetings-page">
      {/* List column */}
      <div className="w-80 border-r border-border bg-card flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <span className="text-sm font-semibold text-foreground">Meetings</span>
          <Button
            variant="default"
            size="sm"
            onClick={() => setShowNewEntity(true)}
            data-testid="new-meeting-button"
          >
            <Plus className="h-4 w-4 mr-1" />
            New Meeting
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
              icon={Calendar}
              heading="No meetings yet"
              body="Capture your first meeting note."
              actionLabel="New Meeting"
              onAction={() => setShowNewEntity(true)}
              className="py-8"
            />
          ) : (
            <div>
              {filtered.map(m => (
                <div
                  key={m.path}
                  className={cn(
                    'px-4 py-2.5 cursor-pointer border-b border-border hover:bg-secondary/50 transition-colors',
                    selectedPath === m.path && 'bg-secondary'
                  )}
                  onClick={() => setSelectedPath(m.path)}
                  data-testid="meeting-row"
                >
                  <div className="flex items-center gap-2.5">
                    {formatDateChip(m.meeting_date) && (() => {
                      const chip = formatDateChip(m.meeting_date)!
                      return (
                        <span className="inline-flex flex-col items-center justify-center w-10 h-10 rounded-md bg-primary/15 text-primary shrink-0">
                          <span className="text-[10px] font-semibold leading-none">{chip.month}</span>
                          <span className="text-sm font-bold leading-none">{chip.day}</span>
                        </span>
                      )
                    })()}
                    <div className="flex flex-1 items-center justify-between min-w-0">
                      <span className="text-sm font-medium text-foreground truncate">{m.title}</span>
                      <div className="flex items-center gap-1 shrink-0 ml-2">
                        {m.participant_count > 0 && (
                          <span className="text-xs text-muted-foreground">{m.participant_count}</span>
                        )}
                        {m.open_actions > 0 && (
                          <span className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground text-xs w-5 h-5">
                            {m.open_actions}
                          </span>
                        )}
                      </div>
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
              icon={Calendar}
              heading="Select a meeting"
              body="Choose a meeting to see notes, participants, and action items."
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
                <div>
                  <h1 className="text-xl font-semibold text-foreground">{meetingDetail?.title ?? ''}</h1>
                  {meetingDetail?.meeting_date && (
                    <p className="text-sm text-muted-foreground mt-0.5">{meetingDetail.meeting_date}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {editingBody === null && (
                    <Button size="sm" variant="outline" onClick={() => setEditingBody(meetingDetail?.body ?? '')}>
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
                title="Participants"
                count={meetingDetail?.participants.length ?? 0}
                sectionId={`meetings-participants-${selectedPath}`}
                defaultOpen={true}
              >
                <div data-testid="participants-section" className="px-4 py-3">
                  {(meetingDetail?.participants.length ?? 0) === 0 ? (
                    <p className="text-sm text-muted-foreground">No participants listed</p>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {meetingDetail!.participants.map((p, i) => (
                        <PersonBadge key={i} name={p} />
                      ))}
                    </div>
                  )}
                  {showAddParticipant ? (
                    <div className="flex items-center gap-2 mt-2">
                      <PersonAutocomplete
                        existingPeople={meetingDetail?.participants ?? []}
                        onAdd={handleAddParticipant}
                        onBlur={() => setShowAddParticipant(false)}
                      />
                      <Button size="sm" variant="ghost" onClick={() => setShowAddParticipant(false)}>Cancel</Button>
                    </div>
                  ) : (
                    <Button variant="outline" size="sm" className="mt-2" onClick={() => setShowAddParticipant(true)}>
                      <Plus className="h-3.5 w-3.5 mr-1.5" />
                      Add Participant
                    </Button>
                  )}
                </div>
              </CollapsibleSection>

              <CollapsibleSection
                title="Actions"
                count={actions.filter(a => !a.done).length}
                sectionId={`meetings-actions-${selectedPath}`}
                defaultOpen={true}
              >
                <div data-testid="meeting-actions-section">
                  {actions.length === 0 ? (
                    <p className="px-4 py-3 text-sm text-muted-foreground">No open actions</p>
                  ) : (
                    <div>
                      {actions.map(action => (
                        <ActionItemRow
                          key={action.id}
                          item={action}
                          onToggle={handleToggleAction}
                          onDelete={handleDeleteAction}
                          onOpen={setDetailAction}
                        />
                      ))}
                    </div>
                  )}
                  {showAddAction ? (
                    <div className="flex items-center gap-2 px-4 py-2 border-t border-border">
                      <input
                        autoFocus
                        value={newActionText}
                        onChange={e => setNewActionText(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') handleAddAction(); if (e.key === 'Escape') setShowAddAction(false) }}
                        placeholder="What needs to be done?"
                        className="flex-1 rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
                      />
                      <Button size="sm" onClick={handleAddAction} disabled={savingAction || !newActionText.trim()}>
                        {savingAction ? 'Saving…' : 'Add'}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setShowAddAction(false)}>Cancel</Button>
                    </div>
                  ) : (
                    <div className="px-4 pb-3">
                      <Button variant="outline" size="sm" onClick={() => setShowAddAction(true)}>
                        <Plus className="h-3.5 w-3.5 mr-1.5" />
                        Add Action
                      </Button>
                    </div>
                  )}
                </div>
              </CollapsibleSection>

              <CollapsibleSection
                title="Tags"
                count={tags.length}
                sectionId={`meetings-tags-${selectedPath}`}
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
                        className="flex-1 text-sm bg-input border border-border rounded px-2 py-1 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                        placeholder="tag-name"
                        value={newTagInput}
                        onChange={e => setNewTagInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') handleAddTag(); if (e.key === 'Escape') { setShowAddTag(false); setNewTagInput('') } }}
                      />
                      <button type="button" onClick={handleAddTag} disabled={savingTags} className="text-xs px-2 py-1 bg-primary text-primary-foreground rounded disabled:opacity-50">Add</button>
                      <button type="button" onClick={() => { setShowAddTag(false); setNewTagInput('') }} className="text-xs px-2 py-1 text-muted-foreground">Cancel</button>
                    </div>
                  ) : (
                    <button type="button" onClick={() => setShowAddTag(true)} className="text-xs text-muted-foreground hover:text-foreground">+ Add tag</button>
                  )}
                </div>
              </CollapsibleSection>

              <CollapsibleSection
                title="Notes"
                count={1}
                sectionId={`meetings-notes-${selectedPath}`}
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
                    {meetingDetail?.body
                      ? <WikiMarkdown>{meetingDetail.body}</WikiMarkdown>
                      : <p className="text-sm text-muted-foreground">No meeting notes yet.</p>
                    }
                  </div>
                )}
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
                  if (!meetingDetail) return
                  setDeleteTarget({ name: meetingDetail.title, path: selectedPath })
                  setShowDeleteConfirm(true)
                }}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Meeting
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
        entityType="meetings"
        onCreated={loadMeetings}
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
            confirmLabel="Delete Meeting"
            cancelLabel="Keep Meeting"
            variant="destructive"
          />
          <DeleteEntityModal
            open={showDeleteEntity}
            onClose={() => { setShowDeleteEntity(false); setDeleteTarget(null) }}
            entityType="meetings"
            entityName={deleteTarget.name}
            entityPath={deleteTarget.path}
            onDeleted={() => {
              loadMeetings()
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
