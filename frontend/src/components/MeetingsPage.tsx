import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, Plus, Trash2 } from 'lucide-react'
import { cn, getAPI } from '@/lib/utils'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { NewEntityModal } from './NewEntityModal'
import { DeleteEntityModal } from './DeleteEntityModal'
import type { MeetingSummary, ActionItem } from '@/types'

function Section({ title, count, children }: { title: string; count: number; children: React.ReactNode }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="border-b">
      <button
        className="flex w-full items-center justify-between px-4 py-2 text-sm font-medium hover:bg-accent"
        onClick={() => setOpen(o => !o)}
      >
        <span>{title} ({count})</span>
        <ChevronDown className={cn('h-4 w-4 transition-transform', open ? 'rotate-180' : '')} />
      </button>
      {open && <div className="px-4 pb-3">{children}</div>}
    </div>
  )
}

export function MeetingsPage() {
  const { setCurrentView } = useUIContext()
  const { openNote } = useNoteContext()

  const [meetings, setMeetings] = useState<MeetingSummary[]>([])
  const [filter, setFilter] = useState('')
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [showNewEntity, setShowNewEntity] = useState(false)
  const [showDeleteEntity, setShowDeleteEntity] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ name: string; path: string } | null>(null)
  const [meetingDetail, setMeetingDetail] = useState<{
    body: string
    title: string
    meeting_date: string
    participants: string[]
    open_actions: number
  } | null>(null)
  const [backlinks, setBacklinks] = useState<{ path: string; title: string }[]>([])
  const [actions, setActions] = useState<ActionItem[]>([])

  const loadMeetings = () => {
    fetch(`${getAPI()}/meetings`)
      .then(r => r.json())
      .then(d => setMeetings(d.meetings ?? []))
      .catch(() => {})
  }

  // Fetch meetings list on mount
  useEffect(() => {
    loadMeetings()
  }, [])

  // Fetch meeting detail on selectedPath change
  useEffect(() => {
    if (!selectedPath) return
    const enc = encodeURIComponent(selectedPath)
    Promise.all([
      fetch(`${getAPI()}/meetings/${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json()),
      fetch(`${getAPI()}/actions?note_path=${enc}`).then(r => r.json()),
    ]).then(([detail, meta, acts]) => {
      setMeetingDetail({
        body: detail.body ?? '',
        title: detail.title ?? '',
        meeting_date: detail.meeting_date ?? '',
        participants: detail.participants ?? [],
        open_actions: detail.open_actions ?? 0,
      })
      setBacklinks(meta.backlinks ?? [])
      setActions(acts.actions ?? [])
    }).catch(() => {})
  }, [selectedPath])

  async function handleOpenInNotes() {
    if (!selectedPath) return
    await openNote(selectedPath)
    setCurrentView('notes')
  }

  const filtered = meetings.filter(m =>
    m.title.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="flex h-full" data-testid="meetings-page">
      {/* Left column — meeting list */}
      <div className="w-80 border-r overflow-y-auto flex flex-col">
        <div className="p-2 border-b flex gap-2">
          <input
            placeholder="Filter by title..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="flex-1 rounded-md border border-input bg-background px-3 py-1 text-sm outline-none focus:ring-1 focus:ring-ring"
          />
          <Button
            size="sm"
            onClick={() => setShowNewEntity(true)}
            data-testid="new-meeting-button"
          >
            <Plus size={16} className="mr-1" /> New Meeting
          </Button>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead className="w-16 text-right">People</TableHead>
              <TableHead className="w-24">Date</TableHead>
              <TableHead className="w-16 text-right">Actions</TableHead>
              <TableHead className="w-8" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map(m => (
              <TableRow
                key={m.path}
                className={cn('cursor-pointer', selectedPath === m.path && 'bg-accent')}
                onClick={() => setSelectedPath(m.path)}
              >
                <TableCell className="font-medium">{m.title}</TableCell>
                <TableCell className="text-right">{m.participant_count}</TableCell>
                <TableCell className="text-muted-foreground">{m.meeting_date}</TableCell>
                <TableCell className="text-right">{m.open_actions}</TableCell>
                <TableCell>
                  <button
                    className="opacity-0 group-hover:opacity-100 hover:text-destructive p-1 rounded"
                    onClick={e => {
                      e.stopPropagation()
                      setDeleteTarget({ name: m.title, path: m.path })
                      setShowDeleteEntity(true)
                    }}
                    data-testid="delete-meeting-button"
                    title={`Delete ${m.title}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-4">
                  No meetings found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Right column — detail panel */}
      <div className="flex-1 overflow-y-auto">
        {!selectedPath ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            Select a meeting to view details
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <h2 className="text-lg font-semibold">{meetingDetail?.title ?? ''}</h2>
              <Button size="sm" variant="outline" onClick={handleOpenInNotes}>
                Open in Notes
              </Button>
            </div>

            <Section title="Note" count={meetingDetail?.body ? 1 : 0}>
              <div className="prose prose-sm dark:prose-invert max-w-none py-2">
                <Markdown remarkPlugins={[remarkGfm]}>{meetingDetail?.body ?? ''}</Markdown>
              </div>
            </Section>

            <Section title="Participants" count={meetingDetail?.participants.length ?? 0}>
              <div data-testid="participants-section">
                {(meetingDetail?.participants.length ?? 0) === 0 ? (
                  <p className="text-sm text-muted-foreground py-1">No participants listed</p>
                ) : (
                  <ul className="space-y-1">
                    {meetingDetail!.participants.map((p, i) => (
                      <li key={i} className="text-sm">{p}</li>
                    ))}
                  </ul>
                )}
              </div>
            </Section>

            <Section title="Action Items" count={actions.filter(a => !a.done).length}>
              <div data-testid="meeting-actions-section">
                {actions.filter(a => !a.done).length === 0 ? (
                  <p className="text-sm text-muted-foreground py-1">No open actions</p>
                ) : (
                  <ul className="space-y-1">
                    {actions.filter(a => !a.done).map(a => (
                      <li key={a.id} className="flex items-start gap-2 text-sm">
                        <input type="checkbox" disabled checked={a.done} className="mt-0.5" />
                        <span>
                          {a.text}
                          {a.due_date && (
                            <span className="ml-2 text-muted-foreground">{a.due_date}</span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Section>

            <Section title="Backlinks" count={backlinks.length}>
              <div data-testid="meeting-backlinks-section">
                {backlinks.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-1">No backlinks</p>
                ) : (
                  <ul className="space-y-1">
                    {backlinks.map(b => (
                      <li key={b.path} className="text-sm">{b.title}</li>
                    ))}
                  </ul>
                )}
              </div>
            </Section>
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
      )}
    </div>
  )
}
