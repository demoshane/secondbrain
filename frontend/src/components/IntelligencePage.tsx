import { useState, useEffect, useCallback } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Brain, RefreshCw, Sparkles, Chrome } from 'lucide-react'
import { cn, getAPI } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { HealthScoreGauge } from '@/components/ui/health-score-gauge'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { EmptyState } from '@/components/ui/empty-state'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { ActionItemRow } from '@/components/ui/action-item-row'
import { ActionDetailModal } from '@/components/ui/action-detail-modal'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { toast } from 'sonner'
import type { BrainHealth, ActionItem } from '@/types'

interface Nudge {
  path: string
  title: string
  updated_at: string
}

function daysSince(dateStr: string): number {
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
}

function getUrgency(dueDate: string | null): { label: string; className: string } | null {
  if (!dueDate) return null
  const due = new Date(dueDate)
  const now = new Date()
  if (due < now) return { label: 'High', className: 'bg-red-500/15 text-red-400' }
  const sevenDays = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
  if (due <= sevenDays) return { label: 'Med', className: 'bg-amber-500/15 text-amber-400' }
  return { label: 'Low', className: 'bg-green-500/15 text-green-400' }
}

export function IntelligencePage() {
  const { setCurrentView } = useUIContext()
  const { openNote } = useNoteContext()

  const goToNote = (path: string) => {
    openNote(path)
    setCurrentView('notes')
  }
  const [recap, setRecap] = useState<string>('')
  const [generatingRecap, setGeneratingRecap] = useState(false)
  const [health, setHealth] = useState<BrainHealth | null>(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [nudges, setNudges] = useState<Nudge[]>([])
  const [priorityActions, setPriorityActions] = useState<ActionItem[]>([])
  const [detailAction, setDetailAction] = useState<ActionItem | null>(null)
  const [captureText, setCaptureText] = useState('')
  const [capturing, setCapturing] = useState(false)
  const [synthesis, setSynthesis] = useState<string>('')
  const [synthesisLoading, setSynthesisLoading] = useState(false)
  const [showExtensionInstructions, setShowExtensionInstructions] = useState(false)
  const [extensionApiReachable, setExtensionApiReachable] = useState(false)

  const fetchPriorityActions = useCallback(() => {
    fetch(`${getAPI()}/actions?done=0&limit=5`)
      .then(r => r.json())
      .then(d => setPriorityActions(d.actions ?? []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    setHealthLoading(true)
    fetch(`${getAPI()}/brain-health`)
      .then(r => r.json())
      .then(d => { setHealth(d); setHealthLoading(false) })
      .catch(() => setHealthLoading(false))
    fetch(`${getAPI()}/intelligence`)
      .then(r => r.json())
      .then(d => setNudges(d.nudges ?? []))
      .catch(() => {})
    fetch(`${getAPI()}/ping`, { signal: AbortSignal.timeout(2000) })
      .then(res => setExtensionApiReachable(res.ok))
      .catch(() => setExtensionApiReachable(false))
    fetchPriorityActions()
  }, [fetchPriorityActions])

  const togglePriorityAction = useCallback(async (id: number) => {
    const action = priorityActions.find(a => a.id === id)
    if (!action) return
    await fetch(`${getAPI()}/actions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ done: !action.done }),
    })
    fetchPriorityActions()
  }, [priorityActions, fetchPriorityActions])

  const deletePriorityAction = useCallback(async (id: number) => {
    await fetch(`${getAPI()}/actions/${id}`, { method: 'DELETE' })
    fetchPriorityActions()
  }, [fetchPriorityActions])

  const handleQuickCapture = useCallback(async () => {
    if (!captureText.trim()) return
    setCapturing(true)
    const title = captureText.split('\n')[0].slice(0, 60) || 'Quick capture'
    try {
      const res = await fetch(`${getAPI()}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: captureText, type: 'note', title }),
      })
      if (!res.ok) throw new Error('capture failed')
      toast.success('Note saved')
      setCaptureText('')
    } catch {
      toast.error('Capture failed. Check the app connection and try again.')
    } finally {
      setCapturing(false)
    }
  }, [captureText])

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
      const healthRes = await fetch(`${getAPI()}/brain-health`)
      setHealth(await healthRes.json())
    } catch {
      toast.error('Merge failed: network error')
    }
  }, [])

  const dismissDuplicate = useCallback(async (dc: { a: string; b: string; similarity: number }) => {
    try {
      const res = await fetch(`${getAPI()}/brain-health/dismiss-duplicate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ a: dc.a, b: dc.b, similarity: dc.similarity }),
      })
      if (!res.ok) {
        toast.error('Failed to dismiss duplicate')
        return
      }
      toast.success('Marked as not duplicate')
      // Remove from local state
      if (health) {
        setHealth({
          ...health,
          duplicate_candidates: health.duplicate_candidates.filter(
            d => !(d.a === dc.a && d.b === dc.b)
          ),
          duplicate_count: health.duplicate_count - 1,
        })
      }
    } catch {
      toast.error('Failed to dismiss duplicate')
    }
  }, [health])

  const generateSynthesis = useCallback(async () => {
    setSynthesisLoading(true)
    try {
      const res = await fetch(`${getAPI()}/intelligence/synthesis`)
      const data = await res.json()
      if (data.synthesis) setSynthesis(data.synthesis)
      else toast.error('Synthesis generation failed.')
    } catch {
      toast.error('Synthesis failed. Check the app connection and try again.')
    } finally {
      setSynthesisLoading(false)
    }
  }, [])

  const generateRecap = useCallback(async () => {
    setGeneratingRecap(true)
    try {
      const res = await fetch(`${getAPI()}/intelligence/recap`, { method: 'POST' })
      const data = await res.json()
      if (data.recap) setRecap(data.recap)
      else toast.error('Recap generation failed.')
    } catch {
      toast.error('Recap failed. Check the app connection and try again.')
    } finally {
      setGeneratingRecap(false)
    }
  }, [])

  const runHealthCheck = useCallback(async () => {
    setHealthLoading(true)
    try {
      const res = await fetch(`${getAPI()}/brain-health`)
      setHealth(await res.json())
    } catch {
      toast.error('Health check failed.')
    } finally {
      setHealthLoading(false)
    }
  }, [])

  const deleteEmptyNotes = async () => {
    const empty = health?.empty_notes ?? []
    if (empty.length === 0) return
    if (!confirm(`Delete ${empty.length} empty note(s)? This cannot be undone.`)) return
    let deleted = 0
    for (const n of empty) {
      const res = await fetch(`${getAPI()}/notes/${encodeURIComponent(n.path)}`, { method: 'DELETE' })
      if (res.ok) deleted++
    }
    toast.success(`Deleted ${deleted} empty note(s)`)
    runHealthCheck()
  }

  return (
    <div className="flex flex-1 overflow-hidden" data-testid="intelligence-page">
      {/* Left column ~65% — Brain Health + Stale Notes + Actions */}
      <div className="flex-[2] overflow-y-auto p-6 bg-background">
        {/* Brain Health card */}
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase mb-4">Brain Health</h2>
          {healthLoading ? (
            <SkeletonList count={3} rowHeight="h-8" className="p-0" />
          ) : health ? (
            <>
              <div className="flex items-start gap-6 mb-6">
                <HealthScoreGauge score={health.score} />
                <div className="flex flex-wrap gap-4">
                  <div className="flex flex-col items-center">
                    <span className="text-2xl font-semibold text-foreground">{health.total_notes}</span>
                    <span className="text-xs text-muted-foreground">Notes</span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className={cn("text-2xl font-semibold", health.orphan_count > 0 ? "text-red-400" : "text-foreground")}>
                      {health.orphan_count}
                    </span>
                    <span className="text-xs text-muted-foreground">Orphans</span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className={cn("text-2xl font-semibold", health.empty_count > 0 ? "text-red-400" : "text-foreground")}>
                      {health.empty_count}
                    </span>
                    <span className="text-xs text-muted-foreground">Empty</span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className={cn("text-2xl font-semibold", health.broken_link_count > 0 ? "text-red-400" : "text-foreground")}>
                      {health.broken_link_count}
                    </span>
                    <span className="text-xs text-muted-foreground">Broken Links</span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className={cn("text-2xl font-semibold", health.duplicate_count > 0 ? "text-amber-400" : "text-foreground")}>
                      {health.duplicate_count}
                    </span>
                    <span className="text-xs text-muted-foreground">Duplicates</span>
                  </div>
                </div>
              </div>

              {/* Orphans */}
              {health.orphan_count > 0 && (
                <div className="mb-2">
                  <CollapsibleSection title="Orphaned Notes" count={health.orphan_count} sectionId="health-orphans" defaultOpen={false}>
                    <ul className="px-3 pb-3 space-y-1">
                      {health.orphans.map(o => (
                        <li key={o.path}>
                          <button className="text-xs text-muted-foreground truncate hover:text-foreground text-left w-full" onClick={() => goToNote(o.path)}>{o.title || o.path}</button>
                        </li>
                      ))}
                    </ul>
                  </CollapsibleSection>
                </div>
              )}

              {/* Empty notes */}
              {health.empty_count > 0 && (
                <div className="mb-2">
                  <CollapsibleSection title="Empty Notes" count={health.empty_count} sectionId="health-empty" defaultOpen={false}>
                    <ul className="px-3 pb-3 space-y-1">
                      {health.empty_notes.map(n => (
                        <li key={n.path}>
                          <button className="text-xs text-muted-foreground truncate hover:text-foreground text-left w-full" onClick={() => goToNote(n.path)}>{n.title || n.path}</button>
                        </li>
                      ))}
                    </ul>
                  </CollapsibleSection>
                </div>
              )}

              {/* Broken links */}
              {health.broken_link_count > 0 && (
                <div className="mb-2">
                  <CollapsibleSection title="Broken Links" count={health.broken_link_count} sectionId="health-broken-links" defaultOpen={false}>
                    <ul className="px-3 pb-3 space-y-1">
                      {health.broken_links.map((bl, i) => (
                        <li key={i} className="text-xs text-muted-foreground truncate">
                          <button className="hover:text-foreground" onClick={() => goToNote(bl.source)}>{bl.source}</button>
                          {' → '}
                          <span>{bl.target}</span>
                        </li>
                      ))}
                    </ul>
                  </CollapsibleSection>
                </div>
              )}

              {/* Duplicates */}
              {health.duplicate_count > 0 && (
                <div className="mb-2">
                  <CollapsibleSection title="Potential Duplicates" count={health.duplicate_count} sectionId="health-duplicates" defaultOpen={false}>
                    <ul className="px-3 pb-3 space-y-1">
                      {health.duplicate_candidates.map((dc, i) => (
                        <li key={i} className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground truncate flex-1">
                            <button className="hover:text-foreground" onClick={() => goToNote(dc.a)}>{dc.a.split('/').pop()?.replace('.md', '')}</button>
                            {' / '}
                            <button className="hover:text-foreground" onClick={() => goToNote(dc.b)}>{dc.b.split('/').pop()?.replace('.md', '')}</button>
                            {' '}({Math.round(dc.similarity * 100)}%)
                          </span>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-xs shrink-0 text-muted-foreground"
                            onClick={() => dismissDuplicate(dc)}
                          >
                            Ignore
                          </Button>
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
                  </CollapsibleSection>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Failed to load health data.</p>
          )}
        </div>

        {/* Stale Notes section */}
        <CollapsibleSection title="Stale Notes" count={nudges.length} sectionId="intelligence-stale-notes" defaultOpen={true}>
          <div className="px-3 pb-3">
            {nudges.length === 0 ? (
              <p className="text-sm text-muted-foreground py-2">No stale notes.</p>
            ) : (
              <ul className="space-y-2">
                {nudges.map(n => (
                  <li key={n.path} className="text-sm flex items-center gap-2">
                    <button className="font-medium text-foreground flex-1 min-w-0 truncate text-left hover:text-primary" onClick={() => goToNote(n.path)}>{n.title}</button>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/15 text-amber-400 shrink-0">
                      {daysSince(n.updated_at)}d
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CollapsibleSection>
      </div>

      {/* Right column ~35% — Synthesis + Recap + Quick Actions */}
      <div className="flex-1 border-l border-border bg-card overflow-y-auto p-6">
        {/* Weekly Synthesis card */}
        <div className="rounded-lg border border-accent/30 bg-accent/5 p-6 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold uppercase flex items-center gap-1.5 text-accent">
              <Sparkles className="h-4 w-4" />
              Weekly Synthesis
            </h2>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 gap-1"
              onClick={generateSynthesis}
              disabled={synthesisLoading}
            >
              <RefreshCw className={cn('h-4 w-4', synthesisLoading && 'animate-spin')} />
              {synthesisLoading ? 'Generating...' : 'Generate'}
            </Button>
          </div>
          {synthesis ? (
            <div className="prose prose-sm prose-invert max-w-none">
              <Markdown remarkPlugins={[remarkGfm]}>{synthesis}</Markdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              Generate a weekly synthesis to see themes, decisions, and open threads from the past 7 days.
            </p>
          )}
        </div>

        {/* Weekly Recap card */}
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase flex items-center gap-2">
              <Brain className="h-4 w-4 text-orange-400" />
              Weekly Recap
            </h2>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 gap-1"
              onClick={generateRecap}
              disabled={generatingRecap}
              data-testid="generate-recap-btn"
            >
              <RefreshCw className={cn('h-4 w-4', generatingRecap && 'animate-spin')} />
              {generatingRecap ? 'Generating...' : 'Refresh'}
            </Button>
          </div>
          {recap ? (
            <div className="prose prose-sm prose-invert max-w-none">
              <Markdown remarkPlugins={[remarkGfm]}>{recap}</Markdown>
            </div>
          ) : (
            <EmptyState
              icon={Brain}
              heading="No recap generated"
              body="Generate a weekly recap to see what your brain has been focused on."
              actionLabel="Generate Recap"
              onAction={generateRecap}
            />
          )}
        </div>

        {/* Priority Actions card */}
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase mb-3">Priority Actions</h3>
          {priorityActions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No open actions</p>
          ) : (
            <>
              {priorityActions.map(a => {
                const urgency = getUrgency(a.due_date)
                return (
                  <div key={a.id} className="flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <ActionItemRow item={a} onToggle={togglePriorityAction} onDelete={deletePriorityAction} onOpen={setDetailAction} />
                    </div>
                    {urgency !== null && (
                      <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0', urgency.className)}>
                        {urgency.label}
                      </span>
                    )}
                  </div>
                )
              })}
              <button
                onClick={() => setCurrentView('actions')}
                className="text-xs text-primary hover:underline mt-2 block"
              >
                Go to Actions View
              </button>
            </>
          )}
        </div>

        {/* Quick Capture card */}
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase mb-3">Quick Capture</h3>
          <textarea
            value={captureText}
            onChange={e => setCaptureText(e.target.value)}
            placeholder="Drop a thought, task, or link here..."
            className="w-full rounded-md border border-input bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring resize-none"
            rows={3}
          />
          <Button
            size="sm"
            className="mt-2 w-full"
            onClick={handleQuickCapture}
            disabled={capturing || !captureText.trim()}
          >
            {capturing ? 'Saving...' : 'Save to Inbox'}
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase mb-3">Quick Actions</h3>
          <div className="flex flex-col gap-2">
            <Button variant="outline" size="sm" onClick={runHealthCheck} disabled={healthLoading}>
              <RefreshCw className={cn('h-4 w-4 mr-2', healthLoading && 'animate-spin')} />
              Run Health Check
            </Button>
            {(health?.empty_count ?? 0) > 0 && (
              <Button variant="outline" size="sm" onClick={deleteEmptyNotes}>
                Delete {health!.empty_count} Empty Note{health!.empty_count !== 1 ? 's' : ''}
              </Button>
            )}
          </div>
        </div>

        {/* Chrome Extension */}
        <div className="bg-card rounded-lg border border-border p-6">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase mb-3">Chrome Extension</h3>
          <p className="text-sm text-muted-foreground mb-3">
            Capture web pages, selections, and Gmail threads directly from Chrome.
          </p>
          <div className="flex items-center gap-2 mb-3">
            <div className={cn(
              'w-2 h-2 rounded-full',
              extensionApiReachable ? 'bg-green-500' : 'bg-red-500'
            )} />
            <span className="text-xs text-muted-foreground">
              {extensionApiReachable ? 'sb-api reachable from browser' : 'sb-api not reachable'}
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowExtensionInstructions(v => !v)}
          >
            <Chrome className="h-4 w-4 mr-2" />
            Install Chrome Extension
          </Button>
          {showExtensionInstructions && (
            <div className="mt-3 p-3 rounded bg-muted text-sm space-y-2">
              <p className="font-medium">Installation steps:</p>
              <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                <li>Open <code className="bg-background px-1 rounded text-xs">chrome://extensions</code> in Chrome</li>
                <li>Enable &ldquo;Developer mode&rdquo; (toggle in top-right)</li>
                <li>Click &ldquo;Load unpacked&rdquo;</li>
                <li>Select the <code className="bg-background px-1 rounded text-xs">chrome-extension/</code> directory in the project root</li>
                <li>The &ldquo;Second Brain Capture&rdquo; extension should appear</li>
              </ol>
            </div>
          )}
        </div>
      </div>

      <ActionDetailModal
        open={!!detailAction}
        action={detailAction}
        onClose={() => setDetailAction(null)}
        onSaved={updated => {
          setPriorityActions(prev => prev.map(a => a.id === updated.id ? updated : a))
          setDetailAction(null)
        }}
      />
    </div>
  )
}
