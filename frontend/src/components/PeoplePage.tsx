import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown } from 'lucide-react'
import { cn, getAPI } from '@/lib/utils'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import type { PersonSummary, ActionItem } from '@/types'

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
  const [filter, setFilter] = useState('')
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [personNote, setPersonNote] = useState<{ body: string; title: string } | null>(null)
  const [meetings, setMeetings] = useState<{ path: string; title: string }[]>([])
  const [backlinks, setBacklinks] = useState<{ path: string; title: string }[]>([])
  const [actions, setActions] = useState<ActionItem[]>([])

  // Fetch people list on mount
  useEffect(() => {
    fetch(`${getAPI()}/people`)
      .then(r => r.json())
      .then(d => setPeople(d.people ?? []))
      .catch(() => {})
  }, [])

  // Fetch person detail on selectedPath change
  useEffect(() => {
    if (!selectedPath) return
    const enc = encodeURIComponent(selectedPath)
    Promise.all([
      fetch(`${getAPI()}/notes/${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json()),
      fetch(`${getAPI()}/actions?assignee=${enc}`).then(r => r.json()),
    ]).then(([note, meta, acts]) => {
      setPersonNote({ body: note.body ?? '', title: note.title ?? '' })
      const bl: { path: string; title: string }[] = meta.backlinks ?? []
      setMeetings(bl.filter(b => b.path.includes('/meetings/')))
      setBacklinks(bl.filter(b => !b.path.includes('/meetings/')))
      setActions(acts.actions ?? [])
    }).catch(() => {})
  }, [selectedPath])

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
        <div className="p-2 border-b">
          <input
            placeholder="Filter by name..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-1 text-sm outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead className="w-16 text-right">Actions</TableHead>
              <TableHead className="w-24">Last Note</TableHead>
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
                <TableCell className="text-right">{p.open_actions}</TableCell>
                <TableCell className="text-muted-foreground">{p.updated_at.slice(0, 10)}</TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground py-4">
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
              <h2 className="text-lg font-semibold">{personNote?.title ?? ''}</h2>
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
          </div>
        )}
      </div>
    </div>
  )
}
