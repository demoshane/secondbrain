import { useState, useEffect, useCallback } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { RefreshCw, ChevronDown } from 'lucide-react'
import { cn, getAPI } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ActionItemList } from './ActionItemList'
import { toast } from 'sonner'
import type { BrainHealth, ActionItem, Note } from '@/types'

interface Nudge {
  path: string
  title: string
  updated_at: string
}

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

export function IntelligencePage() {
  const [recap, setRecap] = useState<string>('')
  const [generatingRecap, setGeneratingRecap] = useState(false)
  const [health, setHealth] = useState<BrainHealth | null>(null)
  const [nudges, setNudges] = useState<Nudge[]>([])
  const [actions, setActions] = useState<ActionItem[]>([])
  const [people, setPeople] = useState<Note[]>([])

  const loadActions = useCallback(async () => {
    const res = await fetch(getAPI() + '/actions')
    const data = await res.json()
    setActions(data.items || data.actions || [])
  }, [])

  const loadPeople = useCallback(async () => {
    const res = await fetch(getAPI() + '/people')
    const data = await res.json()
    setPeople(data.people || [])
  }, [])

  useEffect(() => {
    fetch(`${getAPI()}/brain-health`)
      .then(r => r.json())
      .then(d => setHealth(d))
      .catch(() => {})
    fetch(`${getAPI()}/intelligence`)
      .then(r => r.json())
      .then(d => setNudges(d.nudges ?? []))
      .catch(() => {})
    loadActions()
    loadPeople()
  }, [loadActions, loadPeople])

  const toggleDone = async (action: ActionItem) => {
    await fetch(`${getAPI()}/actions/${action.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ done: !action.done }),
    })
    toast.success(action.done ? 'Marked open' : 'Marked complete')
    loadActions()
  }

  const assignTo = async (action: ActionItem, assigneePath: string) => {
    await fetch(`${getAPI()}/actions/${action.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assignee_path: assigneePath === 'none' ? null : assigneePath }),
    })
    loadActions()
  }

  const handleMerge = useCallback(async (dc: { a: string; b: string; similarity: number }) => {
    const choice = window.confirm(
      `Merge duplicate pair?\n\nA: ${dc.a}\nB: ${dc.b}\n\nClick OK to keep A (discard B), or Cancel to skip.`
    )
    if (!choice) return
    try {
      const res = await fetch(`${getAPI()}/brain-health/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keep_path: dc.a, discard_path: dc.b }),
      })
      if (!res.ok) {
        const err = await res.json()
        toast.error(`Merge failed: ${err.error}`)
        return
      }
      toast.success('Notes merged successfully')
      // Refresh health panel
      const healthRes = await fetch(`${getAPI()}/brain-health`)
      setHealth(await healthRes.json())
    } catch {
      toast.error('Merge failed: network error')
    }
  }, [loadActions])

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
    <div className="h-full overflow-y-auto p-4 space-y-4" data-testid="intelligence-page">
      {/* Recap section */}
      <div className="border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border-b">
          <h2 className="text-sm font-semibold uppercase text-muted-foreground">Recap</h2>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 gap-1"
            onClick={generateRecap}
            disabled={generatingRecap}
            data-testid="generate-recap-btn"
          >
            <RefreshCw className={cn('h-4 w-4', generatingRecap && 'animate-spin')} />
            {generatingRecap ? 'Generating...' : 'Generate Recap'}
          </Button>
        </div>
        <div className="p-4">
          {recap ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <Markdown remarkPlugins={[remarkGfm]}>{recap}</Markdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Click Generate Recap to create a summary of recent activity.</p>
          )}
        </div>
      </div>

      {/* Brain Health section */}
      <div className="border rounded-lg overflow-hidden">
        <div className="px-4 py-2 bg-muted/50 border-b">
          <h2 className="text-sm font-semibold uppercase text-muted-foreground">Brain Health</h2>
        </div>
        <div className="p-4 space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-3xl font-bold" data-testid="health-score">
              {health?.score ?? '...'}
            </span>
            <span className="text-muted-foreground text-sm">/100</span>
            {health && (
              <span className="text-xs text-muted-foreground ml-2">
                ({health.total_notes} notes)
              </span>
            )}
          </div>

          {health && (
            <div className="space-y-2">
              {/* Orphans */}
              {health.orphan_count > 0 && (
                <Section title="Orphaned Notes" count={health.orphan_count}>
                  <ul className="space-y-1 mt-1">
                    {health.orphans.map(o => (
                      <li key={o.path} className="text-xs text-muted-foreground truncate">{o.title || o.path}</li>
                    ))}
                  </ul>
                </Section>
              )}
              {health.orphan_count === 0 && (
                <p className="text-xs text-muted-foreground">Orphans: 0</p>
              )}

              {/* Empty notes */}
              {health.empty_count > 0 && (
                <Section title="Empty Notes" count={health.empty_count}>
                  <ul className="space-y-1 mt-1">
                    {health.empty_notes.map(n => (
                      <li key={n.path} className="text-xs text-muted-foreground truncate">{n.title || n.path}</li>
                    ))}
                  </ul>
                </Section>
              )}
              {health.empty_count === 0 && (
                <p className="text-xs text-muted-foreground">Empty notes: 0</p>
              )}

              {/* Broken links */}
              {health.broken_link_count > 0 && (
                <Section title="Broken Links" count={health.broken_link_count}>
                  <ul className="space-y-1 mt-1">
                    {health.broken_links.map((bl, i) => (
                      <li key={i} className="text-xs text-muted-foreground truncate">{bl.source} &rarr; {bl.target}</li>
                    ))}
                  </ul>
                </Section>
              )}
              {health.broken_link_count === 0 && (
                <p className="text-xs text-muted-foreground">Broken links: 0</p>
              )}

              {/* Duplicates */}
              {health.duplicate_count > 0 && (
                <Section title="Duplicate Candidates" count={health.duplicate_count}>
                  <ul className="space-y-1 mt-1">
                    {health.duplicate_candidates.map((dc, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground truncate flex-1">
                          {dc.a} / {dc.b} ({Math.round(dc.similarity * 100)}%)
                        </span>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-xs shrink-0"
                          onClick={() => handleMerge(dc)}
                        >
                          Merge
                        </Button>
                      </li>
                    ))}
                  </ul>
                </Section>
              )}
              {health.duplicate_count === 0 && (
                <p className="text-xs text-muted-foreground">Duplicates: 0</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Stale Notes section */}
      <div className="border rounded-lg overflow-hidden">
        <div className="px-4 py-2 bg-muted/50 border-b">
          <h2 className="text-sm font-semibold uppercase text-muted-foreground">Stale Notes</h2>
        </div>
        <div className="p-4">
          {nudges.length === 0 ? (
            <p className="text-sm text-muted-foreground">No stale notes.</p>
          ) : (
            <ul className="space-y-2">
              {nudges.map(n => (
                <li key={n.path} className="text-sm">
                  <span className="font-medium">{n.title}</span>
                  <span className="ml-2 text-xs text-muted-foreground">{n.updated_at}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Action Items section */}
      <div className="border rounded-lg overflow-hidden">
        <div className="px-4 py-2 bg-muted/50 border-b">
          <h2 className="text-sm font-semibold uppercase text-muted-foreground">Action Items</h2>
        </div>
        <div className="p-4">
          <ActionItemList
            actions={actions.filter(a => !a.done)}
            people={people}
            onToggle={toggleDone}
            onAssign={assignTo}
          />
        </div>
      </div>
    </div>
  )
}
