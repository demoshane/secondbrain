import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { RefreshCw } from 'lucide-react'
import { useNoteContext } from '@/contexts/NoteContext'
import { getAPI } from '@/lib/utils'
import type { Note } from '@/types'

interface Connection {
  from: string
  to: string
  reason?: string
}

export function RightPanel() {
  const { currentPath } = useNoteContext()
  const [backlinks, setBacklinks] = useState<Note[]>([])
  const [people, setPeople] = useState<Note[]>([])
  const [recap, setRecap] = useState<string>('')
  const [connections, setConnections] = useState<Connection[]>([])
  const [digest, setDigest] = useState<string>('')
  const [healthScore, setHealthScore] = useState<number | null>(null)
  const [generatingRecap, setGeneratingRecap] = useState(false)

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

  useEffect(() => {
    fetch(`${getAPI()}/brain-health`)
      .then(r => r.json())
      .then(d => setHealthScore(d.score ?? null))
      .catch(() => {})
    fetch(`${getAPI()}/intelligence`)
      .then(r => r.json())
      .then(d => {
        setRecap(d.recap ?? '')
        setConnections(d.connections ?? [])
        setDigest(d.digest ?? '')
      })
      .catch(() => {})
  }, [])

  const generateRecap = useCallback(async () => {
    setGeneratingRecap(true)
    try {
      const res = await fetch(`${getAPI()}/intelligence/recap`, { method: 'POST' })
      const data = await res.json()
      setRecap(data.recap ?? recap)
    } catch {
      // keep existing recap
    }
    setGeneratingRecap(false)
  }, [recap])

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
        <section>
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-xs font-semibold uppercase text-muted-foreground">Recap</h3>
            <Button
              size="icon"
              variant="ghost"
              className="h-5 w-5"
              onClick={generateRecap}
              disabled={generatingRecap}
              data-testid="generate-recap-btn"
            >
              <RefreshCw className={`h-3 w-3 ${generatingRecap ? 'animate-spin' : ''}`} />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground whitespace-pre-wrap" data-testid="recap-text">
            {recap || 'No recap yet'}
          </p>
        </section>
        {connections.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-1">Connections</h3>
            <ul className="space-y-1" data-testid="connections-list">
              {connections.map((c, i) => (
                <li key={i} className="text-xs text-muted-foreground truncate">
                  {c.from} &rarr; {c.to}{c.reason ? ` (${c.reason})` : ''}
                </li>
              ))}
            </ul>
          </section>
        )}
        {digest && (
          <section>
            <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-1">Digest</h3>
            <p className="text-xs text-muted-foreground whitespace-pre-wrap" data-testid="digest-text">{digest}</p>
          </section>
        )}
        {healthScore !== null && (
          <section>
            <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-1">Brain Health</h3>
            <p className="text-sm font-medium">{healthScore}/100</p>
          </section>
        )}
      </div>
    </ScrollArea>
  )
}
