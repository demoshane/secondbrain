import { useState, useEffect, useRef, useCallback } from 'react'
import { ChevronLeft, ChevronRight, Link, Users, CheckSquare, Unlink, Tag } from 'lucide-react'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { PersonBadge } from '@/components/ui/person-badge'
import { TagBadge } from '@/components/ui/tag-badge'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { ActionDetailModal } from '@/components/ui/action-detail-modal'
import { EmptyState } from '@/components/ui/empty-state'
import { useNoteContext } from '@/contexts/NoteContext'
import { useSearchContext } from '@/contexts/SearchContext'
import { getAPI, encodePath } from '@/lib/utils'
import { toast } from 'sonner'
import type { Note, ActionItem } from '@/types'

export function RightPanel() {
  const { currentPath, openNote, notes } = useNoteContext()
  const { setTagFilter } = useSearchContext()
  const [backlinks, setBacklinks] = useState<Note[]>([])
  const [connections, setConnections] = useState<Note[]>([])
  const [connQuery, setConnQuery] = useState('')
  const [connResults, setConnResults] = useState<Note[]>([])
  const [showConnDropdown, setShowConnDropdown] = useState(false)
  const connSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const connInputRef = useRef<HTMLInputElement>(null)
  const [connDropdownRect, setConnDropdownRect] = useState<DOMRect | null>(null)
  const [people, setPeople] = useState<Note[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [noteActions, setNoteActions] = useState<ActionItem[]>([])
  const [detailAction, setDetailAction] = useState<ActionItem | null>(null)
  const [importance, setImportance] = useState<string>('medium')
  const [tagInput, setTagInput] = useState('')
  const [tagSuggestions, setTagSuggestions] = useState<string[]>([])
  const [showTagDropdown, setShowTagDropdown] = useState(false)
  const tagSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const tagInputRef = useRef<HTMLInputElement>(null)
  const [tagDropdownRect, setTagDropdownRect] = useState<DOMRect | null>(null)
  const [personQuery, setPersonQuery] = useState('')
  const [personResults, setPersonResults] = useState<Note[]>([])
  const [showPersonDropdown, setShowPersonDropdown] = useState(false)
  const personSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const personInputRef = useRef<HTMLInputElement>(null)
  const [personDropdownRect, setPersonDropdownRect] = useState<DOMRect | null>(null)
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('rp-collapsed') === 'true'
    } catch {
      return false
    }
  })

  const reloadMeta = useCallback(() => {
    if (!currentPath) return
    const encoded = encodePath(currentPath)
    fetch(`${getAPI()}/notes/${encoded}/meta`)
      .then(r => r.json())
      .then(d => {
        setBacklinks(d.backlinks ?? [])
        setConnections(d.connections ?? [])
        setPeople(d.people ?? [])
        setTags(d.tags ?? [])
      })
      .catch(() => {
        setBacklinks([])
        setPeople([])
        setTags([])
      })
  }, [currentPath])

  useEffect(() => {
    const note = notes.find(n => n.path === currentPath)
    if (note) setImportance(note.importance || 'medium')
  }, [currentPath, notes])

  useEffect(() => {
    if (!currentPath) return
    reloadMeta()
    fetch(`${getAPI()}/actions`)
      .then(r => r.json())
      .then(d => {
        const all: ActionItem[] = d.actions ?? []
        setNoteActions(all.filter(a => a.note_path === currentPath))
      })
      .catch(() => setNoteActions([]))
  }, [currentPath, reloadMeta])

  const reloadActions = () => {
    if (!currentPath) return
    fetch(`${getAPI()}/actions`)
      .then(r => r.json())
      .then(d => {
        const all: ActionItem[] = d.actions ?? []
        setNoteActions(all.filter(a => a.note_path === currentPath))
      })
      .catch(() => {})
  }

  const toggleDone = async (id: number) => {
    const action = noteActions.find(a => a.id === id)
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
      toast.error('Something went wrong -- try again')
    }
  }

  const deleteAction = async (id: number) => {
    try {
      await fetch(`${getAPI()}/actions/${id}`, { method: 'DELETE' })
      reloadActions()
    } catch {
      toast.error('Something went wrong -- try again')
    }
  }

  const addTag = async (tag: string) => {
    const trimmed = tag.trim().toLowerCase()
    if (!trimmed || !currentPath) return
    if (tags.includes(trimmed)) return
    const updatedTags = [...tags, trimmed]
    const encoded = encodePath(currentPath)
    try {
      await fetch(`${getAPI()}/notes/${encoded}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags: updatedTags }),
      })
      reloadMeta()
    } catch {
      toast.error('Failed to save tag')
    }
  }

  const removeTag = async (tag: string) => {
    if (!currentPath) return
    const updatedTags = tags.filter(t => t !== tag)
    const encoded = encodePath(currentPath)
    try {
      await fetch(`${getAPI()}/notes/${encoded}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags: updatedTags }),
      })
      reloadMeta()
    } catch {
      toast.error('Failed to remove tag')
    }
  }

  const addPerson = async (personPath: string) => {
    if (!currentPath) return
    if (people.some(p => p.path === personPath)) return
    const updatedPaths = [...people.map(p => p.path), personPath]
    const encoded = encodePath(currentPath)
    try {
      await fetch(`${getAPI()}/notes/${encoded}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ people: updatedPaths }),
      })
      setPersonQuery('')
      setPersonResults([])
      setShowPersonDropdown(false)
      reloadMeta()
    } catch {
      toast.error('Failed to link person')
    }
  }

  const removePerson = async (personPath: string) => {
    if (!currentPath) return
    const updatedPaths = people.filter(p => p.path !== personPath).map(p => p.path)
    const encoded = encodePath(currentPath)
    try {
      await fetch(`${getAPI()}/notes/${encoded}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ people: updatedPaths }),
      })
      reloadMeta()
    } catch {
      toast.error('Failed to unlink person')
    }
  }

  const addConnection = async (targetPath: string) => {
    if (!currentPath) return
    if (connections.some(c => c.path === targetPath)) return
    const encoded = encodePath(currentPath)
    try {
      await fetch(`${getAPI()}/notes/${encoded}/connections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: targetPath }),
      })
      setConnQuery('')
      setConnResults([])
      setShowConnDropdown(false)
      reloadMeta()
    } catch {
      toast.error('Failed to add connection')
    }
  }

  const removeConnection = async (targetPath: string) => {
    if (!currentPath) return
    const encoded = encodePath(currentPath)
    try {
      await fetch(`${getAPI()}/notes/${encoded}/connections`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: targetPath }),
      })
      reloadMeta()
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
          r.path !== currentPath && !connections.some(c => c.path === r.path)
        )
        setConnResults(filtered)
        setShowConnDropdown(filtered.length > 0)
      } catch {
        setConnResults([])
      }
    }, 250)
  }

  const handleTagQueryChange = (q: string) => {
    setTagInput(q)
    if (tagSearchRef.current) clearTimeout(tagSearchRef.current)
    if (!q.trim()) {
      setTagSuggestions([])
      setShowTagDropdown(false)
      return
    }
    if (tagInputRef.current) setTagDropdownRect(tagInputRef.current.getBoundingClientRect())
    tagSearchRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${getAPI()}/tags`)
        const data = await res.json()
        const allTags: string[] = data.tags ?? []
        const lower = q.toLowerCase()
        const filtered = allTags.filter(t => t.toLowerCase().includes(lower) && !tags.includes(t))
        setTagSuggestions(filtered.slice(0, 8))
        setShowTagDropdown(filtered.length > 0)
      } catch {
        setTagSuggestions([])
      }
    }, 150)
  }

  const handlePersonQueryChange = (q: string) => {
    setPersonQuery(q)
    if (personSearchRef.current) clearTimeout(personSearchRef.current)
    if (!q.trim()) {
      setPersonResults([])
      setShowPersonDropdown(false)
      return
    }
    if (personInputRef.current) setPersonDropdownRect(personInputRef.current.getBoundingClientRect())
    personSearchRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${getAPI()}/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, note_type: 'person', limit: 5 }),
        })
        const data = await res.json()
        setPersonResults(data.results ?? [])
        setShowPersonDropdown(true)
      } catch {
        setPersonResults([])
      }
    }, 250)
  }

  const toggleCollapsed = () => {
    setCollapsed(prev => {
      const next = !prev
      try {
        localStorage.setItem('rp-collapsed', String(next))
      } catch {
        // ignore
      }
      return next
    })
  }

  // Only show empty state when no note is selected at all
  const allEmpty = !currentPath

  if (collapsed) {
    return (
      <div
        className="w-10 border-l border-border bg-card flex flex-col items-center py-2 gap-3 transition-all duration-200"
        data-testid="right-panel"
      >
        <button
          type="button"
          onClick={toggleCollapsed}
          className="p-1 rounded hover:bg-secondary/50 text-muted-foreground"
          aria-label="Expand panel"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        {backlinks.length > 0 && (
          <Link className="h-4 w-4 text-muted-foreground" />
        )}
        {tags.length > 0 && (
          <Tag className="h-4 w-4 text-muted-foreground" />
        )}
        {people.length > 0 && (
          <Users className="h-4 w-4 text-muted-foreground" />
        )}
        {noteActions.length > 0 && (
          <CheckSquare className="h-4 w-4 text-muted-foreground" />
        )}
      </div>
    )
  }

  return (
    <div
      className="w-64 border-l border-border bg-card flex flex-col overflow-y-auto transition-all duration-200"
      data-testid="right-panel"
    >
      {/* Header row */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <span className="text-xs font-semibold text-muted-foreground uppercase">Connections</span>
        <button
          type="button"
          onClick={toggleCollapsed}
          className="p-1 rounded hover:bg-secondary/50 text-muted-foreground"
          aria-label="Collapse panel"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {currentPath && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <span className="text-xs text-muted-foreground font-medium">Importance</span>
          <select
            value={importance}
            onChange={async (e) => {
              const val = e.target.value
              const API = getAPI()
              const enc = encodePath(currentPath)
              try {
                const res = await fetch(`${API}/notes/${enc}/importance`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ importance: val }),
                })
                if (res.ok) {
                  setImportance(val)
                  toast.success(`Importance set to ${val}`)
                }
              } catch { toast.error('Failed to update importance') }
            }}
            className="bg-secondary text-foreground text-xs rounded px-2 py-1 border border-border appearance-none cursor-pointer"
          >
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      )}

      {allEmpty ? (
        <EmptyState
          icon={Unlink}
          heading="No note selected"
          body="Open a note to see its tags, linked people, backlinks, and actions."
        />
      ) : (
        <div className="flex flex-col">
          {backlinks.length > 0 && (
            <CollapsibleSection
              title="Backlinks"
              count={backlinks.length}
              sectionId="rp-backlinks"
              defaultOpen={true}
            >
              {backlinks.map(b => (
                <button
                  key={b.path}
                  className="block w-full text-left px-3 py-1.5 text-sm truncate text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                  onClick={() => openNote(b.path)}
                  data-testid="backlink-item"
                >
                  {b.title}
                </button>
              ))}
            </CollapsibleSection>
          )}

          {/* Connections section */}
          {currentPath && (
            <CollapsibleSection
              title="Connections"
              count={connections.length}
              sectionId="rp-connections"
              defaultOpen={true}
            >
              {connections.map(c => (
                <div key={c.path} className="flex items-center group px-3 py-1.5 hover:bg-secondary/50">
                  <button
                    className="flex-1 text-left text-sm truncate text-muted-foreground hover:text-foreground"
                    onClick={() => openNote(c.path)}
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
              <div className="px-3 pb-2">
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
          )}

          {/* Tags section — always visible when a note is open */}
          {currentPath && (
            <CollapsibleSection
              title="Tags"
              count={tags.length}
              sectionId="rp-tags"
              defaultOpen={true}
            >
              <div className="flex flex-wrap gap-1 px-3 py-2">
                {tags.map(t => (
                  <TagBadge
                    key={t}
                    tag={t}
                    onClick={() => setTagFilter(t)}
                    onRemove={() => removeTag(t)}
                  />
                ))}
              </div>
              <div className="px-3 pb-2">
                <input
                  ref={tagInputRef}
                  type="text"
                  placeholder="+ tag"
                  value={tagInput}
                  className="w-full text-xs bg-transparent border border-border rounded px-2 py-1 text-muted-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50"
                  onChange={e => handleTagQueryChange(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      addTag(tagInput)
                      setTagInput('')
                      setShowTagDropdown(false)
                    }
                  }}
                  onBlur={() => setTimeout(() => {
                    setTagInput('')
                    setShowTagDropdown(false)
                  }, 150)}
                />
                {showTagDropdown && tagSuggestions.length > 0 && tagDropdownRect && (
                  <div
                    style={{ position: 'fixed', top: tagDropdownRect.bottom + 2, left: tagDropdownRect.left, width: tagDropdownRect.width, zIndex: 9999 }}
                    className="bg-card border border-border rounded shadow-lg max-h-40 overflow-y-auto"
                  >
                    {tagSuggestions.map(t => (
                      <button
                        key={t}
                        type="button"
                        className="block w-full text-left px-2 py-1.5 text-xs hover:bg-secondary/50 text-foreground truncate"
                        onMouseDown={() => { addTag(t); setTagInput(''); setShowTagDropdown(false) }}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </CollapsibleSection>
          )}

          {/* People section */}
          {currentPath && (
            <CollapsibleSection
              title="People"
              count={people.length}
              sectionId="rp-people"
              defaultOpen={true}
            >
              <div className="flex flex-wrap gap-1 px-3 py-2">
                {people.map(p => (
                  <PersonBadge
                    key={p.path}
                    name={p.title}
                    path={p.path}
                    onClick={() => openNote(p.path)}
                    onRemove={() => removePerson(p.path)}
                  />
                ))}
              </div>
              <div className="px-3 pb-2">
                <input
                  ref={personInputRef}
                  type="text"
                  placeholder="+ person"
                  value={personQuery}
                  className="w-full text-xs bg-transparent border border-border rounded px-2 py-1 text-muted-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50"
                  onChange={e => handlePersonQueryChange(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && personResults.length > 0) {
                      addPerson(personResults[0].path)
                    }
                  }}
                  onBlur={() => setTimeout(() => setShowPersonDropdown(false), 150)}
                />
                {showPersonDropdown && personResults.length > 0 && personDropdownRect && (
                  <div
                    style={{ position: 'fixed', top: personDropdownRect.bottom + 2, left: personDropdownRect.left, width: personDropdownRect.width, zIndex: 9999 }}
                    className="bg-card border border-border rounded shadow-lg max-h-40 overflow-y-auto"
                  >
                    {personResults.map(r => (
                      <button
                        key={r.path}
                        type="button"
                        className="block w-full text-left px-2 py-1.5 text-xs hover:bg-secondary/50 text-foreground truncate"
                        onMouseDown={() => addPerson(r.path)}
                      >
                        {r.title}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </CollapsibleSection>
          )}

          {noteActions.length > 0 && (
            <CollapsibleSection
              title="Actions"
              count={noteActions.length}
              sectionId="rp-actions"
              defaultOpen={true}
            >
              {noteActions.map(item => (
                <ActionItemRow
                  key={item.id}
                  item={item}
                  onToggle={toggleDone}
                  onDelete={deleteAction}
                  onOpen={setDetailAction}
                />
              ))}
            </CollapsibleSection>
          )}
        </div>
      )}

      <ActionDetailModal
        open={!!detailAction}
        action={detailAction}
        onClose={() => setDetailAction(null)}
        onSaved={updated => {
          setNoteActions(prev => prev.map(a => a.id === updated.id ? updated : a))
          setDetailAction(null)
        }}
      />
    </div>
  )
}
