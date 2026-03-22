import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, Plus, Trash2 } from 'lucide-react'
import { cn, getAPI } from '@/lib/utils'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { ActionItemList } from './ActionItemList'
import { NewEntityModal } from './NewEntityModal'
import { DeleteEntityModal } from './DeleteEntityModal'
import { toast } from 'sonner'
import type { PersonSummary, ActionItem, Note } from '@/types'

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

export function PeoplePage() {
  const { setCurrentView } = useUIContext()
  const { openNote } = useNoteContext()

  const [people, setPeople] = useState<PersonSummary[]>([])
  const [peopleNotes, setPeopleNotes] = useState<Note[]>([])
  const [filter, setFilter] = useState('')
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [selectedPerson, setSelectedPerson] = useState<PersonSummary | null>(null)
  const [personNote, setPersonNote] = useState<{ body: string; title: string } | null>(null)
  const [meetings, setMeetings] = useState<{ path: string; title: string }[]>([])
  const [backlinks, setBacklinks] = useState<{ path: string; title: string }[]>([])
  const [actions, setActions] = useState<ActionItem[]>([])
  const [showNewEntity, setShowNewEntity] = useState(false)
  const [showDeleteEntity, setShowDeleteEntity] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ name: string; path: string } | null>(null)

  const loadPeople = () => {
    fetch(`${getAPI()}/people`)
      .then(r => r.json())
      .then(d => setPeople(d.people ?? []))
      .catch(() => {})
    fetch(`${getAPI()}/notes`)
      .then(r => r.json())
      .then(d => setPeopleNotes((d.notes ?? []).filter((n: Note) => n.type === 'people')))
      .catch(() => {})
  }

  // Fetch people list on mount
  useEffect(() => {
    loadPeople()
  }, [])

  // Fetch person detail on selectedPath change
  useEffect(() => {
    if (!selectedPath) return
    const person = people.find(p => p.path === selectedPath) ?? null
    setSelectedPerson(person)
    const enc = encodeURIComponent(selectedPath)
    Promise.all([
      fetch(`${getAPI()}/notes/${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json()),
      fetch(`${getAPI()}/actions?assignee=${enc}`).then(r => r.json()),
    ]).then(([note, meta, acts]) => {
      setPersonNote({ body: note.body ?? '', title: note.title ?? '' })
      // Use meta.meetings if available (type='meeting' filtered server-side),
      // otherwise fall back to filtering backlinks by type
      const metaMeetings: { path: string; title: string }[] = meta.meetings ?? []
      const bl: { path: string; title: string }[] = meta.backlinks ?? []
      if (metaMeetings.length > 0) {
        setMeetings(metaMeetings)
        setBacklinks(bl)
      } else {
        // Fallback: filter backlinks by type field if available, else path heuristic
        setMeetings(bl.filter(b => (b as { path: string; title: string; type?: string }).type === 'meeting'))
        setBacklinks(bl.filter(b => (b as { path: string; title: string; type?: string }).type !== 'meeting'))
      }
      setActions(acts.actions ?? [])
    }).catch(() => {})
  }, [selectedPath, people])

  const reloadActions = () => {
    if (!selectedPath) return
    const enc = encodeURIComponent(selectedPath)
    fetch(`${getAPI()}/actions?assignee=${enc}`)
      .then(r => r.json())
      .then(d => setActions(d.actions ?? []))
      .catch(() => {})
  }

  const toggleDone = async (action: ActionItem) => {
    try {
      await fetch(`${getAPI()}/actions/${action.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done: !action.done }),
      })
      toast.success(action.done ? 'Marked open' : 'Marked complete')
      reloadActions()
    } catch {
      toast.error('Something went wrong -- try again')
    }
  }

  const assignTo = async (action: ActionItem, assigneePath: string) => {
    await fetch(`${getAPI()}/actions/${action.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assignee_path: assigneePath === 'none' ? null : assigneePath }),
    })
    reloadActions()
  }

  async function handleOpenInNotes() {
    if (!selectedPath) return
    await openNote(selectedPath)
    setCurrentView('notes')
  }

  const filtered = people.filter(p =>
    p.title.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="flex h-full" data-testid="people-page">
      {/* Left column — directory */}
      <div className="w-72 border-r overflow-y-auto flex flex-col">
        <div className="p-2 border-b flex gap-2">
          <input
            placeholder="Filter by name..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="flex-1 rounded-md border border-input bg-background px-3 py-1 text-sm outline-none focus:ring-1 focus:ring-ring"
          />
          <Button
            size="sm"
            onClick={() => setShowNewEntity(true)}
            data-testid="new-person-button"
          >
            <Plus size={16} className="mr-1" /> New Person
          </Button>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Org</TableHead>
              <TableHead className="w-24">Last Interaction</TableHead>
              <TableHead className="w-16 text-right">Actions</TableHead>
              <TableHead className="w-8" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map(p => (
              <TableRow
                key={p.path}
                className={cn('cursor-pointer', selectedPath === p.path && 'bg-accent')}
                onClick={() => setSelectedPath(p.path)}
              >
                <TableCell className="font-medium">{p.title}</TableCell>
                <TableCell className="text-muted-foreground">{p.org || '—'}</TableCell>
                <TableCell className="text-muted-foreground">
                  {p.last_interaction ? p.last_interaction.slice(0, 10) : '—'}
                </TableCell>
                <TableCell className="text-right">
                  {p.open_actions > 0 ? (
                    <span className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground text-xs w-5 h-5">
                      {p.open_actions}
                    </span>
                  ) : '—'}
                </TableCell>
                <TableCell>
                  <button
                    className="opacity-0 group-hover:opacity-100 hover:text-destructive p-1 rounded"
                    onClick={e => {
                      e.stopPropagation()
                      setDeleteTarget({ name: p.title, path: p.path })
                      setShowDeleteEntity(true)
                    }}
                    data-testid="delete-person-button"
                    title={`Delete ${p.title}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-4">
                  No people found
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
            Select a person to view details
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <div>
                <h2 className="text-lg font-semibold">{personNote?.title ?? ''}</h2>
                <div className="flex gap-4 mt-1 text-sm text-muted-foreground">
                  {selectedPerson?.org && (
                    <span>
                      <span className="font-medium">Organization:</span> {selectedPerson.org}
                    </span>
                  )}
                  {selectedPerson?.last_interaction && (
                    <span>
                      <span className="font-medium">Last Interaction:</span>{' '}
                      {selectedPerson.last_interaction.slice(0, 10)}
                    </span>
                  )}
                  {selectedPerson !== null && (
                    <span>
                      <span className="font-medium">Mentions:</span> {selectedPerson.mention_count}
                    </span>
                  )}
                </div>
              </div>
              <Button size="sm" variant="outline" onClick={handleOpenInNotes}>
                Open in Notes
              </Button>
            </div>

            <Section title="Note" count={personNote?.body ? 1 : 0}>
              <div data-testid="note-body-section" className="prose prose-sm dark:prose-invert max-w-none py-2">
                <Markdown remarkPlugins={[remarkGfm]}>{personNote?.body ?? ''}</Markdown>
              </div>
            </Section>

            <Section title="Meetings" count={meetings.length}>
              <div data-testid="meetings-section">
                {meetings.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-1">No meetings yet</p>
                ) : (
                  <ul className="space-y-1">
                    {meetings.map(m => (
                      <li key={m.path} className="text-sm">{m.title}</li>
                    ))}
                  </ul>
                )}
              </div>
            </Section>

            <Section title="Backlinks" count={backlinks.length}>
              <div data-testid="backlinks-section">
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

            <Section title="Open Actions" count={actions.filter(a => !a.done).length}>
              <div data-testid="actions-section">
                <ActionItemList
                  actions={actions.filter(a => !a.done)}
                  people={peopleNotes}
                  onToggle={toggleDone}
                  onAssign={assignTo}
                />
              </div>
            </Section>
          </div>
        )}
      </div>

      <NewEntityModal
        open={showNewEntity}
        onClose={() => setShowNewEntity(false)}
        entityType="people"
        onCreated={loadPeople}
      />
      {deleteTarget && (
        <DeleteEntityModal
          open={showDeleteEntity}
          onClose={() => { setShowDeleteEntity(false); setDeleteTarget(null) }}
          entityType="people"
          entityName={deleteTarget.name}
          entityPath={deleteTarget.path}
          onDeleted={() => {
            loadPeople()
            if (selectedPath === deleteTarget.path) setSelectedPath(null)
          }}
        />
      )}
    </div>
  )
}
