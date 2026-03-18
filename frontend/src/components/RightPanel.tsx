import { useState, useEffect } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { useNoteContext } from '@/contexts/NoteContext'
import { getAPI } from '@/lib/utils'
import type { Note } from '@/types'

export function RightPanel() {
  const { currentPath } = useNoteContext()
  const [backlinks, setBacklinks] = useState<Note[]>([])
  const [people, setPeople] = useState<Note[]>([])

  useEffect(() => {
    if (!currentPath) return
    const encoded = encodeURIComponent(currentPath)
    fetch(`${getAPI()}/notes/${encoded}/backlinks`)
      .then(r => r.json())
      .then(d => setBacklinks(d.backlinks ?? []))
      .catch(() => setBacklinks([]))
    fetch(`${getAPI()}/notes/${encoded}/people`)
      .then(r => r.json())
      .then(d => setPeople(d.people ?? []))
      .catch(() => setPeople([]))
  }, [currentPath])

  return (
    <ScrollArea className="w-64 border-l flex-shrink-0" data-testid="right-panel">
      <div className="p-3 space-y-4">
        {backlinks.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-1">Backlinks</h3>
            {backlinks.map(b => (
              <div key={b.path} className="text-sm truncate text-foreground">{b.title}</div>
            ))}
          </section>
        )}
        {people.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-1">People</h3>
            <div className="flex flex-wrap gap-1">
              {people.map(p => <Badge key={p.path} variant="outline">{p.title}</Badge>)}
            </div>
          </section>
        )}
      </div>
    </ScrollArea>
  )
}
