import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Briefcase, Plus, Trash2, Link } from 'lucide-react'
import { cn, getAPI, encodePath } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EmptyState } from '@/components/ui/empty-state'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { NoteTypeBadge } from '@/components/ui/note-type-badge'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { NewEntityModal } from './NewEntityModal'
import { DeleteEntityModal } from './DeleteEntityModal'
import { toast } from 'sonner'
import type { ProjectSummary, ActionItem, MeetingSummary } from '@/types'

type LinkedMeeting = { path: string; title: string; meeting_date: string }

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
  const [backlinks, setBacklinks] = useState<{ path: string; title: string }[]>([])
  const [actions, setActions] = useState<ActionItem[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  // Link meeting UI state
  const [showLinkMeeting, setShowLinkMeeting] = useState(false)
  const [availableMeetings, setAvailableMeetings] = useState<MeetingSummary[]>([])
  const [selectedMeetingToLink, setSelectedMeetingToLink] = useState<string>('')
  const [linkingMeeting, setLinkingMeeting] = useState(false)

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
    const enc = encodePath(path)
    Promise.all([
      fetch(`${getAPI()}/projects/${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json()),
      fetch(`${getAPI()}/actions?note_path=${enc}`).then(r => r.json()),
    ]).then(([detail, meta, acts]) => {
      setProjectDetail({
        body: detail.body ?? '',
        title: detail.title ?? '',
        updated_at: detail.updated_at ?? '',
        status: detail.status ?? 'active',
        linked_meetings: detail.linked_meetings ?? [],
      })
      setBacklinks(meta.backlinks ?? [])
      setActions(acts.actions ?? [])
    }).catch(() => {})
      .finally(() => setDetailLoading(false))
  }

  useEffect(() => {
    if (!selectedPath) return
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

  async function handleOpenInNotes() {
    if (!selectedPath) return
    await openNote(selectedPath)
    setCurrentView('notes')
  }

  const handleShowLinkMeeting = () => {
    fetch(`${getAPI()}/meetings?limit=50`)
      .then(r => r.json())
      .then(d => setAvailableMeetings(d.meetings ?? []))
      .catch(() => {})
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
                <Button size="sm" variant="outline" onClick={handleOpenInNotes}>
                  Open in Notes
                </Button>
              </div>
            </div>

            <div className="flex-1 divide-y divide-border">
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
                        />
                      ))}
                    </div>
                  )}
                </div>
              </CollapsibleSection>

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
                        <li key={m.path} className="flex items-center gap-2 text-sm">
                          <NoteTypeBadge type="meeting" />
                          <span className="text-foreground">{m.title}</span>
                          {m.meeting_date && (
                            <span className="text-xs text-muted-foreground">{m.meeting_date}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}

                  {!showLinkMeeting ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleShowLinkMeeting}
                    >
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
                      <Button
                        size="sm"
                        onClick={handleLinkMeeting}
                        disabled={!selectedMeetingToLink || linkingMeeting}
                      >
                        Link
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowLinkMeeting(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              </CollapsibleSection>

              {projectDetail?.body && (
                <CollapsibleSection
                  title="Related Notes"
                  count={backlinks.length}
                  sectionId={`projects-related-${selectedPath}`}
                  defaultOpen={false}
                >
                  <div data-testid="project-backlinks-section" className="px-4 py-3">
                    {backlinks.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No related notes</p>
                    ) : (
                      <ul className="space-y-1.5">
                        {backlinks.map(b => (
                          <li key={b.path} className="text-sm text-foreground">{b.title}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </CollapsibleSection>
              )}
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
    </div>
  )
}
