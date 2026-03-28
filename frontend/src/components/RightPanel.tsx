import { useState, useEffect, useRef, useCallback } from 'react'
import { ChevronLeft, ChevronRight, Link, Users, CheckSquare, Unlink, Tag } from 'lucide-react'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { PersonBadge } from '@/components/ui/person-badge'
import { TagBadge } from '@/components/ui/tag-badge'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { EmptyState } from '@/components/ui/empty-state'
import { useNoteContext } from '@/contexts/NoteContext'
import { getAPI, encodePath } from '@/lib/utils'
import { toast } from 'sonner'
import type { Note, ActionItem } from '@/types'

export function RightPanel() {
  const { currentPath, openNote } = useNoteContext()
  const [backlinks, setBacklinks] = useState<Note[]>([])
  const [people, setPeople] = useState<Note[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [noteActions, setNoteActions] = useState<ActionItem[]>([])
  const [tagInput, setTagInput] = useState('')
  const [personQuery, setPersonQuery] = useState('')
  const [personResults, setPersonResults] = useState<Note[]>([])
  const [showPersonDropdown, setShowPersonDropdown] = useState(false)
  const personSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null)
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

  const handlePersonQueryChange = (q: string) => {
    setPersonQuery(q)
    if (personSearchRef.current) clearTimeout(personSearchRef.current)
    if (!q.trim()) {
      setPersonResults([])
      setShowPersonDropdown(false)
      return
    }
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

  // Panel is "empty" only when nothing to show AND no note selected (tags section always visible when a note is open)
  const allEmpty = !currentPath && backlinks.length === 0 && people.length === 0 && noteActions.length === 0

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

      {allEmpty ? (
        <EmptyState
          icon={Unlink}
          heading="No connections yet"
          body="Add tags or link this note to others to see backlinks, people, and actions here."
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
                    onRemove={() => removeTag(t)}
                  />
                ))}
              </div>
              <div className="px-3 pb-2">
                <input
                  type="text"
                  placeholder="+ tag"
                  value={tagInput}
                  className="w-full text-xs bg-transparent border border-border rounded px-2 py-1 text-muted-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50"
                  onChange={e => setTagInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      addTag(tagInput)
                      setTagInput('')
                    }
                  }}
                  onBlur={() => {
                    if (tagInput.trim()) {
                      addTag(tagInput)
                      setTagInput('')
                    }
                  }}
                />
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
              <div className="px-3 pb-2 relative">
                <input
                  type="text"
                  placeholder="+ person"
                  value={personQuery}
                  className="w-full text-xs bg-transparent border border-border rounded px-2 py-1 text-muted-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50"
                  onChange={e => handlePersonQueryChange(e.target.value)}
                  onBlur={() => setTimeout(() => setShowPersonDropdown(false), 150)}
                />
                {showPersonDropdown && personResults.length > 0 && (
                  <div className="absolute left-3 right-3 top-full mt-0.5 bg-card border border-border rounded shadow-lg z-50 max-h-40 overflow-y-auto">
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
                />
              ))}
            </CollapsibleSection>
          )}
        </div>
      )}
    </div>
  )
}
