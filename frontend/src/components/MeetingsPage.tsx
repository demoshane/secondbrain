import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Calendar, Plus, Trash2 } from 'lucide-react'
import { cn, getAPI, encodePath } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EmptyState } from '@/components/ui/empty-state'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { PersonBadge } from '@/components/ui/person-badge'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { NewEntityModal } from './NewEntityModal'
import { DeleteEntityModal } from './DeleteEntityModal'
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
  const [detailLoading, setDetailLoading] = useState(false)

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
    const enc = encodePath(selectedPath)
    Promise.all([
      fetch(`${getAPI()}/meetings/${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/actions?note_path=${enc}`).then(r => r.json()),
    ]).then(([detail, acts]) => {
      setMeetingDetail({
        body: detail.body ?? '',
        title: detail.title ?? '',
        meeting_date: detail.meeting_date ?? '',
        participants: detail.participants ?? [],
      })
      setActions(acts.actions ?? [])
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

  async function handleOpenInNotes() {
    if (!selectedPath) return
    await openNote(selectedPath)
    setCurrentView('notes')
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
                  <div className="flex items-center justify-between">
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
                  {m.meeting_date && (
                    <div className="text-xs text-muted-foreground mt-0.5">{m.meeting_date}</div>
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
                <Button size="sm" variant="outline" onClick={handleOpenInNotes}>
                  Open in Notes
                </Button>
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
                </div>
              </CollapsibleSection>

              <CollapsibleSection
                title="Actions"
                count={actions.filter(a => !a.done).length}
                sectionId={`meetings-actions-${selectedPath}`}
                defaultOpen={true}
              >
                <div data-testid="meeting-actions-section">
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
                        />
                      ))}
                    </div>
                  )}
                </div>
              </CollapsibleSection>

              {meetingDetail?.body && (
                <CollapsibleSection
                  title="Notes"
                  count={1}
                  sectionId={`meetings-notes-${selectedPath}`}
                  defaultOpen={true}
                >
                  <div className="px-4 py-3 prose prose-sm prose-invert max-w-none leading-relaxed">
                    <Markdown remarkPlugins={[remarkGfm]}>{meetingDetail.body}</Markdown>
                  </div>
                </CollapsibleSection>
              )}
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
    </div>
  )
}
