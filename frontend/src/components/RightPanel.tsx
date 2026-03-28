import { useState, useEffect } from 'react'
import { ChevronLeft, ChevronRight, Link, Users, CheckSquare, Unlink } from 'lucide-react'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { PersonBadge } from '@/components/ui/person-badge'
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
  const [noteActions, setNoteActions] = useState<ActionItem[]>([])
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('rp-collapsed') === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    if (!currentPath) return
    const encoded = encodePath(currentPath)
    fetch(`${getAPI()}/notes/${encoded}/meta`)
      .then(r => r.json())
      .then(d => {
        setBacklinks(d.backlinks ?? [])
        setPeople(d.people ?? [])
      })
      .catch(() => {
        setBacklinks([])
        setPeople([])
      })
    fetch(`${getAPI()}/actions`)
      .then(r => r.json())
      .then(d => {
        const all: ActionItem[] = d.actions ?? []
        setNoteActions(all.filter(a => a.note_path === currentPath))
      })
      .catch(() => setNoteActions([]))
  }, [currentPath])

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

  const allEmpty = backlinks.length === 0 && people.length === 0 && noteActions.length === 0

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

          {people.length > 0 && (
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
                  />
                ))}
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
