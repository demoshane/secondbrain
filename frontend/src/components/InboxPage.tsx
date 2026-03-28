import { useState, useEffect, useCallback, useRef } from 'react'
import { Inbox } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { EmptyState } from '@/components/ui/empty-state'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { getAPI, encodePath } from '@/lib/utils'
import { NoteViewer } from './NoteViewer'
import { useNoteContext } from '@/contexts/NoteContext'
import type { ActionItem, InboxData, NoteSummary, Note } from '@/types'

// ─── Types ────────────────────────────────────────────────────────────────────

type InboxItem =
  | { kind: 'action'; id: string; path: string; title: string; text: string }
  | { kind: 'note'; id: string; path: string; title: string }

// ─── Backlink picker (inline search) ─────────────────────────────────────────

function BacklinkPicker({
  onSelect,
  onCancel,
}: {
  notePath: string
  onSelect: (targetPath: string) => void
  onCancel: () => void
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Note[]>([])
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (query.length < 2) {
      setResults([])
      return
    }
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${getAPI()}/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query }),
        })
        const data = await res.json()
        setResults((data.results ?? []).slice(0, 10))
      } catch {
        // ignore
      }
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query])

  return (
    <div className="mt-1 flex flex-col gap-1">
      <input
        autoFocus
        className="w-full rounded border px-2 py-1 text-xs bg-input"
        placeholder="Search notes… (min 2 chars)"
        value={query}
        onChange={e => setQuery(e.target.value)}
      />
      {results.length > 0 && (
        <div className="rounded border bg-background shadow-sm max-h-40 overflow-y-auto">
          {results.map((r: Note) => (
            <button
              key={r.path}
              className="block w-full px-2 py-1 text-left text-xs hover:bg-accent truncate"
              onClick={() => onSelect(r.path)}
            >
              {r.title || r.path}
            </button>
          ))}
        </div>
      )}
      <Button size="sm" variant="ghost" className="h-6 text-xs self-start" onClick={onCancel}>
        Cancel
      </Button>
    </div>
  )
}

// ─── InboxPage ────────────────────────────────────────────────────────────────

export function InboxPage() {
  const { currentNote, openNote } = useNoteContext()
  const [data, setData] = useState<InboxData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState<InboxItem | null>(null)
  const [checkedAt, setCheckedAt] = useState<string | null>(null)

  // Actions section state
  const [actionsOffset, setActionsOffset] = useState(0)
  const [actionsAccum, setActionsAccum] = useState<ActionItem[]>([])
  const [sourceFilter, setSourceFilter] = useState('')
  const sourceDebounce = useRef<ReturnType<typeof setTimeout> | null>(null)

  // People for assignee picker
  const [people, setPeople] = useState<Note[]>([])

  // Backlink picker state: keyed by note path
  const [backlinkOpen, setBacklinkOpen] = useState<string | null>(null)

  const loadInbox = useCallback(
    async (offset = 0, sourceNote = '') => {
      setLoading(true)
      try {
        const params = new URLSearchParams()
        if (offset) params.set('actions_offset', String(offset))
        if (sourceNote) params.set('source_note', sourceNote)
        const res = await fetch(`${getAPI()}/inbox?${params}`)
        const json: InboxData = await res.json()
        if (offset === 0) {
          setActionsAccum(json.unassigned_actions)
        } else {
          setActionsAccum(prev => [...prev, ...json.unassigned_actions])
        }
        setData(json)
        setCheckedAt(new Date().toLocaleTimeString())
      } catch {
        // keep previous data on error
      } finally {
        setLoading(false)
      }
    },
    []
  )

  useEffect(() => {
    if (selectedItem) openNote(selectedItem.path)
  }, [selectedItem, openNote])

  useEffect(() => {
    loadInbox(0, '')
    fetch(`${getAPI()}/notes`)
      .then(r => r.json())
      .then(d =>
        setPeople(
          (d.notes ?? []).filter(
            (n: Note) => n.type === 'person'
          )
        )
      )
      .catch(() => {})
  }, [loadInbox])

  const dismiss = useCallback(
    async (path: string, itemType: 'note' | 'action') => {
      await fetch(`${getAPI()}/inbox/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, item_type: itemType }),
      })
      setActionsOffset(0)
      loadInbox(0, sourceFilter)
    },
    [loadInbox, sourceFilter]
  )

  const assignAction = useCallback(
    async (actionId: number, assigneePath: string | null) => {
      await fetch(`${getAPI()}/actions/${actionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignee_path: assigneePath }),
      })
      loadInbox(0, sourceFilter)
    },
    [loadInbox, sourceFilter]
  )

  const addBacklink = useCallback(
    async (sourcePath: string, targetPath: string) => {
      await fetch(`${getAPI()}/relationships`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_path: sourcePath, target_path: targetPath }),
      })
      setBacklinkOpen(null)
      loadInbox(0, sourceFilter)
    },
    [loadInbox, sourceFilter]
  )

  const deleteNote = useCallback(
    async (note: NoteSummary) => {
      if (!window.confirm(`Delete '${note.title}'? This cannot be undone.`)) return
      const encoded = encodePath(note.path)
      await fetch(`${getAPI()}/notes/${encoded}`, { method: 'DELETE' })
      loadInbox(0, sourceFilter)
    },
    [loadInbox, sourceFilter]
  )

  const deleteAllEmptyNotes = useCallback(
    async () => {
      const notes = data?.empty_notes ?? []
      if (notes.length === 0) return
      if (!window.confirm(`Delete all ${notes.length} empty notes? This cannot be undone.`)) return
      for (const note of notes) {
        const encoded = encodePath(note.path)
        await fetch(`${getAPI()}/notes/${encoded}`, { method: 'DELETE' })
      }
      loadInbox(0, sourceFilter)
    },
    [data?.empty_notes, loadInbox, sourceFilter]
  )

  const handleSourceFilterChange = (val: string) => {
    setSourceFilter(val)
    if (sourceDebounce.current) clearTimeout(sourceDebounce.current)
    sourceDebounce.current = setTimeout(() => {
      setActionsOffset(0)
      loadInbox(0, val)
    }, 300)
  }

  const loadMoreActions = () => {
    const newOffset = actionsOffset + 20
    setActionsOffset(newOffset)
    loadInbox(newOffset, sourceFilter)
  }

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    } catch {
      return iso
    }
  }

  const totalCount = data?.total_count ?? 0
  const allClear = totalCount === 0 && !loading

  return (
    <div className="flex flex-1 overflow-hidden" data-testid="inbox-page">
      {/* List column */}
      <div className="w-80 border-r border-border bg-card flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-border flex-shrink-0">
          {allClear ? (
            <div>
              <p className="text-sm font-semibold text-foreground">
                Inbox{' '}
                <span className="inline-flex items-center justify-center rounded-full bg-secondary text-muted-foreground px-2 text-xs min-w-[1.25rem]">
                  0
                </span>
              </p>
              {checkedAt && (
                <p className="text-xs text-muted-foreground mt-0.5">Last checked {checkedAt}</p>
              )}
            </div>
          ) : (
            <p className="text-sm font-semibold text-foreground">
              Inbox{' '}
              <span className="inline-flex items-center justify-center rounded-full bg-secondary text-muted-foreground px-2 text-xs min-w-[1.25rem]">
                {totalCount}
              </span>
            </p>
          )}
        </div>

        {/* Sections */}
        <div className="flex-1 overflow-y-auto">
          {loading && !data ? (
            <SkeletonList count={5} rowHeight="h-12" className="p-3" />
          ) : (
            <>
              {/* Section 1 — Unassigned Actions */}
              <CollapsibleSection
                title="Unassigned Actions"
                count={data?.unassigned_actions_total ?? 0}
                sectionId="inbox-unassigned-actions"
                defaultOpen={true}
              >
                <div className="px-3 pb-3">
                  <div className="mb-2">
                    <input
                      className="w-full rounded border border-border px-2 py-1 text-xs bg-input"
                      placeholder="Filter by source note…"
                      value={sourceFilter}
                      onChange={e => handleSourceFilterChange(e.target.value)}
                    />
                  </div>
                  {actionsAccum.length === 0 ? (
                    <p className="text-xs text-muted-foreground py-2">Nothing to triage here.</p>
                  ) : (
                    <div className="flex flex-col gap-1">
                      {actionsAccum.map(action => (
                        <div
                          key={action.id}
                          className="rounded border border-border p-2 text-xs cursor-pointer hover:bg-secondary/30"
                          onClick={() =>
                            setSelectedItem({
                              kind: 'action',
                              id: String(action.id),
                              path: action.note_path,
                              title: action.note_path.split('/').pop()?.replace('.md', '') ?? action.note_path,
                              text: action.text,
                            })
                          }
                        >
                          <p className="font-medium line-clamp-2 text-foreground">{action.text}</p>
                          <p className="text-muted-foreground truncate mt-0.5 text-xs">
                            {action.note_path.split('/').pop()?.replace('.md', '') ?? action.note_path}
                          </p>
                          <div className="flex items-center gap-1 mt-1" onClick={e => e.stopPropagation()}>
                            <Select
                              value={action.assignee_path ?? 'none'}
                              onValueChange={v => assignAction(action.id, v === 'none' ? null : v)}
                            >
                              <SelectTrigger className="h-6 w-28 text-xs">
                                <SelectValue placeholder="Assign…" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="none">Unassigned</SelectItem>
                                {people.map(p => (
                                  <SelectItem key={p.path} value={p.path}>
                                    {p.title}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 text-xs px-2"
                              onClick={() => dismiss(String(action.id), 'action')}
                            >
                              Dismiss
                            </Button>
                          </div>
                        </div>
                      ))}
                      {data && data.unassigned_actions_total > actionsOffset + 20 && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs mt-1"
                          onClick={loadMoreActions}
                        >
                          Load more
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              </CollapsibleSection>

              {/* Section 2 — Unprocessed Notes */}
              <CollapsibleSection
                title="Unprocessed Notes"
                count={data?.unprocessed_notes.length ?? 0}
                sectionId="inbox-unprocessed-notes"
                defaultOpen={true}
              >
                <div className="px-3 pb-3">
                  {(data?.unprocessed_notes.length ?? 0) === 0 ? (
                    <p className="text-xs text-muted-foreground py-2">Nothing to triage here.</p>
                  ) : (
                    <div className="flex flex-col gap-1">
                      {data!.unprocessed_notes.map(note => (
                        <div key={note.path} className="rounded border border-border p-2 text-xs">
                          <div
                            className="cursor-pointer hover:text-primary"
                            onClick={() =>
                              setSelectedItem({
                                kind: 'note',
                                id: note.path,
                                path: note.path,
                                title: note.title,
                              })
                            }
                          >
                            <p className="font-medium truncate text-foreground">{note.title}</p>
                            <p className="text-muted-foreground">{formatDate(note.created_at)}</p>
                          </div>
                          {backlinkOpen === note.path ? (
                            <BacklinkPicker
                              notePath={note.path}
                              onSelect={targetPath => addBacklink(note.path, targetPath)}
                              onCancel={() => setBacklinkOpen(null)}
                            />
                          ) : (
                            <div className="flex gap-1 mt-1">
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-6 text-xs px-2"
                                onClick={() => setBacklinkOpen(note.path)}
                              >
                                Add Backlink
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 text-xs px-2"
                                onClick={() => dismiss(note.path, 'note')}
                              >
                                Dismiss
                              </Button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CollapsibleSection>

              {/* Section 3 — Empty Notes */}
              <CollapsibleSection
                title="Empty Notes"
                count={data?.empty_notes.length ?? 0}
                sectionId="inbox-empty-notes"
                defaultOpen={true}
              >
                <div className="px-3 pb-3">
                  {(data?.empty_notes.length ?? 0) === 0 ? (
                    <p className="text-xs text-muted-foreground py-2">Nothing to triage here.</p>
                  ) : (
                    <div className="flex flex-col gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-6 text-xs w-full text-destructive border-destructive/40 hover:bg-destructive/10"
                        onClick={deleteAllEmptyNotes}
                      >
                        Delete all
                      </Button>
                      {data!.empty_notes.map(note => (
                        <div key={note.path} className="rounded border border-border p-2 text-xs">
                          <div
                            className="cursor-pointer hover:text-primary"
                            onClick={() =>
                              setSelectedItem({
                                kind: 'note',
                                id: note.path,
                                path: note.path,
                                title: note.title,
                              })
                            }
                          >
                            <p className="font-medium truncate text-foreground">{note.title}</p>
                          </div>
                          <div className="flex gap-1 mt-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 text-xs px-2 text-destructive hover:text-destructive"
                              onClick={() => deleteNote(note)}
                            >
                              Delete
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 text-xs px-2"
                              onClick={() => dismiss(note.path, 'note')}
                            >
                              Dismiss
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CollapsibleSection>
            </>
          )}
        </div>
      </div>

      {/* Detail column */}
      <div className="flex-1 bg-background overflow-y-auto p-6">
        {currentNote && selectedItem && currentNote.path.endsWith(selectedItem.path) ? (
          <NoteViewer note={currentNote} />
        ) : (
          <div className="flex h-full items-center justify-center">
            <EmptyState
              icon={Inbox}
              heading="Inbox ready"
              body="Select an item from the list to preview its contents and triage it into your Second Brain."
            />
          </div>
        )}
      </div>
    </div>
  )
}
