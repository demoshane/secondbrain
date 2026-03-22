import { useState, useEffect } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { useNoteContext } from '@/contexts/NoteContext'
import { ActionItemList } from './ActionItemList'
import { getAPI } from '@/lib/utils'
import { toast } from 'sonner'
import type { Note, ActionItem } from '@/types'

export function RightPanel() {
  const { currentPath, openNote } = useNoteContext()
  const [backlinks, setBacklinks] = useState<Note[]>([])
  const [people, setPeople] = useState<Note[]>([])
  const [noteActions, setNoteActions] = useState<ActionItem[]>([])
  const [actionPeople, setActionPeople] = useState<Note[]>([])

  useEffect(() => {
    if (!currentPath) return
    const encoded = encodeURIComponent(currentPath)
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
    // Fetch actions for the current note
    fetch(`${getAPI()}/actions`)
      .then(r => r.json())
      .then(d => {
        const all: ActionItem[] = d.actions ?? []
        setNoteActions(all.filter(a => a.note_path === currentPath))
      })
      .catch(() => setNoteActions([]))
  }, [currentPath])

  // Fetch people notes once for assignee picker
  useEffect(() => {
    fetch(`${getAPI()}/notes`)
      .then(r => r.json())
      .then(d => setActionPeople((d.notes ?? []).filter((n: Note) => n.type === 'people')))
      .catch(() => {})
  }, [])

  const reloadNoteActions = () => {
    if (!currentPath) return
    fetch(`${getAPI()}/actions`)
      .then(r => r.json())
      .then(d => {
        const all: ActionItem[] = d.actions ?? []
        setNoteActions(all.filter(a => a.note_path === currentPath))
      })
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
      reloadNoteActions()
    } catch {
      toast.error('Something went wrong -- try again')
    }
  }

  const assignTo = async (action: ActionItem, assigneePath: string) => {
    try {
      await fetch(`${getAPI()}/actions/${action.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignee_path: assigneePath === 'none' ? null : assigneePath }),
      })
      reloadNoteActions()
    } catch {
      toast.error('Something went wrong -- try again')
    }
  }

  return (
    <ScrollArea className="w-64 border-l flex-shrink-0" data-testid="right-panel">
      <div className="p-3 space-y-4">
        {backlinks.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-1">Backlinks</h3>
            {backlinks.map(b => (
              <button
                key={b.path}
                className="block w-full text-left text-sm truncate text-foreground hover:text-primary hover:underline py-0.5"
                onClick={() => openNote(b.path)}
                data-testid="backlink-item"
              >
                {b.title}
              </button>
            ))}
          </section>
        )}
        {people.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-1">People</h3>
            <div className="flex flex-wrap gap-1">
              {people.map(p => (
                <Badge
                  key={p.path}
                  variant="outline"
                  className="cursor-pointer hover:bg-accent"
                  onClick={() => openNote(p.path)}
                  data-testid="people-badge"
                >
                  {p.title}
                </Badge>
              ))}
            </div>
          </section>
        )}
        {noteActions.length > 0 && (
          <section data-testid="right-panel-action-items">
            <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-1">Action Items</h3>
            <ActionItemList
              actions={noteActions}
              people={actionPeople}
              onToggle={toggleDone}
              onAssign={assignTo}
            />
          </section>
        )}
      </div>
    </ScrollArea>
  )
}
