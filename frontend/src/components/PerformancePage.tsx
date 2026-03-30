import { useState, useEffect } from 'react'
import { getAPI } from '@/lib/utils'
import { CollapsibleSection } from '@/components/ui/collapsible-section'

// ── Types ──────────────────────────────────────────────────────────────────────

interface ToolResult {
  tool: string
  elapsed_ms: number
  limit_ms: number
  status: 'pass' | 'warn' | 'error'
  error: string | null
}

interface PerfResult {
  run_at: string
  tool_results: ToolResult[]
}

interface LatestData {
  latest: PerfResult | null
  previous: PerfResult | null
}

// ── Sparkline component ────────────────────────────────────────────────────────

function Sparkline({ values, width = 120, height = 32 }: { values: number[]; width?: number; height?: number }) {
  if (values.length < 2) return <span className="text-muted-foreground text-xs">--</span>
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = max - min || 1
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width
      const y = height - ((v - min) / range) * height
      return `${x},${y}`
    })
    .join(' ')
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={points} fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5" />
    </svg>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function statusClass(status: string): string {
  if (status === 'pass') return 'text-green-400'
  if (status === 'warn') return 'text-amber-400'
  return 'text-red-400'
}

function statusLabel(status: string): string {
  if (status === 'pass') return '✓ pass'
  if (status === 'warn') return '⚠ warn'
  return '✗ error'
}

// NOTE (D-18): Delta is computed client-side from the raw JSON results.
// The GUI is intentionally read-only — it reads stored JSON from the API
// and computes deltas locally, avoiding any server-side processing beyond file reads.
function computeDelta(tool: string, latestMs: number, previous: PerfResult | null): { delta: number | null; colorClass: string } {
  if (!previous) return { delta: null, colorClass: 'text-muted-foreground' }
  const prevTool = previous.tool_results.find(t => t.tool === tool)
  if (!prevTool) return { delta: null, colorClass: 'text-muted-foreground' }
  const delta = latestMs - prevTool.elapsed_ms
  const colorClass = delta > 0
    ? 'text-red-400'
    : delta < 0
      ? 'text-green-400'
      : 'text-muted-foreground'
  return { delta, colorClass }
}

// ── Main component ─────────────────────────────────────────────────────────────

export function PerformancePage() {
  const [latestData, setLatestData] = useState<LatestData | null>(null)
  const [allResults, setAllResults] = useState<Map<string, number[]>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const api = getAPI()

    // Fetch latest + previous
    fetch(`${api}/perf/results/latest`)
      .then(r => {
        if (!r.ok) throw new Error(`${r.status}`)
        return r.json() as Promise<LatestData>
      })
      .then(data => {
        setLatestData(data)
        setLoading(false)
      })
      .catch(() => {
        setError('Could not load performance data. Is sb-api running?')
        setLoading(false)
      })

    // Fetch all dates for sparkline history
    fetch(`${api}/perf/results`)
      .then(r => r.json() as Promise<{ dates: string[] }>)
      .then(({ dates }) => Promise.all(
        dates.map(d =>
          fetch(`${api}/perf/results/${d}`)
            .then(r => r.ok ? r.json() as Promise<PerfResult> : null)
            .catch(() => null)
        )
      ))
      .then(results => {
        const history = new Map<string, number[]>()
        for (const result of results) {
          if (!result) continue
          for (const tr of result.tool_results) {
            if (!history.has(tr.tool)) history.set(tr.tool, [])
            history.get(tr.tool)!.push(tr.elapsed_ms)
          }
        }
        setAllResults(history)
      })
      .catch(() => {
        // Sparkline data is non-critical — silently ignore errors
      })
  }, [])

  // ── Loading state ────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex-1 overflow-auto p-6">
        <div className="mb-6">
          <div className="animate-pulse h-6 w-32 bg-muted rounded mb-2" />
          <div className="animate-pulse h-4 w-64 bg-muted rounded" />
        </div>
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="animate-pulse h-10 bg-muted rounded" />
          ))}
        </div>
      </div>
    )
  }

  // ── Error state ──────────────────────────────────────────────────────────────

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <p className="text-muted-foreground text-sm">{error}</p>
      </div>
    )
  }

  // ── Empty state ──────────────────────────────────────────────────────────────

  if (!latestData?.latest) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <h2 className="text-lg font-semibold mb-2">No benchmark data yet</h2>
        <p className="text-muted-foreground text-sm">
          Run <code className="text-xs bg-muted px-1 py-0.5 rounded">sb-perf</code> in your terminal to record the first result.
        </p>
      </div>
    )
  }

  const { latest, previous } = latestData
  const toolResults = latest.tool_results

  // ── Main render ──────────────────────────────────────────────────────────────

  return (
    <div className="flex-1 overflow-auto">
      {/* Page header */}
      <div className="p-6">
        <h1 className="text-xl font-semibold">Performance</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Benchmark results from <code className="text-xs bg-muted px-1 py-0.5 rounded">sb-perf</code>.{' '}
          Run <code className="text-xs bg-muted px-1 py-0.5 rounded">sb-perf</code> in a terminal to update.
        </p>
      </div>

      {/* Latest Run section */}
      <CollapsibleSection
        title="Latest Run"
        count={toolResults.length}
        sectionId="perf-latest"
        defaultOpen={true}
      >
        <div className="px-3 pb-4">
          <p className="text-xs text-muted-foreground mb-3">
            Run at: {new Date(latest.run_at).toLocaleString()}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground text-left">
                  <th className="py-2 px-3 font-medium">Tool</th>
                  <th className="py-2 px-3 font-medium text-right">Latest</th>
                  <th className="py-2 px-3 font-medium text-right">Previous</th>
                  <th className="py-2 px-3 font-medium text-right">Delta</th>
                  <th className="py-2 px-3 font-medium text-right">Limit</th>
                  <th className="py-2 px-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {toolResults.map(tr => {
                  const { delta, colorClass } = computeDelta(tr.tool, tr.elapsed_ms, previous)
                  const prevTool = previous?.tool_results.find(p => p.tool === tr.tool)
                  return (
                    <tr key={tr.tool} className="border-b border-border">
                      <td className="py-3 px-3 font-mono text-xs">{tr.tool}</td>
                      <td className="py-3 px-3 text-right">{Math.round(tr.elapsed_ms)} ms</td>
                      <td className="py-3 px-3 text-right text-muted-foreground">
                        {prevTool ? `${Math.round(prevTool.elapsed_ms)} ms` : '--'}
                      </td>
                      <td className={`py-3 px-3 text-right ${colorClass}`}>
                        {delta !== null
                          ? `${delta >= 0 ? '+' : ''}${Math.round(delta)} ms`
                          : '--'}
                      </td>
                      <td className="py-3 px-3 text-right text-muted-foreground">{tr.limit_ms} ms</td>
                      <td className={`py-3 px-3 ${statusClass(tr.status)}`}>
                        {statusLabel(tr.status)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </CollapsibleSection>

      {/* 30-Day Trend section */}
      <CollapsibleSection
        title="30-Day Trend"
        count={allResults.size}
        sectionId="perf-trend"
        defaultOpen={true}
      >
        <div className="px-3 pb-4">
          {allResults.size === 0 ? (
            <p className="text-muted-foreground text-sm py-2">Not enough data for trends</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
              {Array.from(allResults.entries()).map(([tool, values]) => (
                <div key={tool} className="bg-card rounded-lg p-4 border border-border">
                  <p className="text-sm font-medium font-mono mb-2">{tool}</p>
                  <Sparkline values={values} />
                </div>
              ))}
            </div>
          )}
        </div>
      </CollapsibleSection>
    </div>
  )
}
