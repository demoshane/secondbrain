import { useState, useEffect } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { useNoteContext } from '@/contexts/NoteContext'
import { getAPI } from '@/lib/utils'
import type { Note } from '@/types'

export function RightPanel() {
  const { currentPath, openNote } = useNoteContext()
  const [backlinks, setBacklinks] = useState<Note[]>([])
  const [people, setPeople] = useState<Note[]>([])

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
  }, [currentPath])

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
      </div>
    </ScrollArea>
  )
}
