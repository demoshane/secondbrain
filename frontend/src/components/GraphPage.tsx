import { useState, useEffect, useMemo } from 'react'
import { getAPI } from '@/lib/utils'
import { GraphCanvas } from './GraphCanvas'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FileText, X } from 'lucide-react'
import { InfoTip } from '@/components/ui/info-tip'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import type { GraphNode, GraphData } from '@/types'

export function GraphPage() {
  const { setCurrentView } = useUIContext()
  const { openNote } = useNoteContext()

  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [filterRelTypes, setFilterRelTypes] = useState<Set<string>>(new Set())
  const [filterNoteTypes, setFilterNoteTypes] = useState<Set<string>>(new Set())

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetch(`${getAPI()}/graph/overview`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((d: GraphData) => {
        setGraphData(d)
        setLoading(false)
      })
      .catch(() => {
        setError('Could not load graph data.')
        setLoading(false)
      })
  }, [])

  const relTypes = useMemo(
    () => (graphData ? [...new Set(graphData.edges.map((e) => e.type))].sort() : []),
    [graphData]
  )
  const noteTypes = useMemo(
    () => (graphData ? [...new Set(graphData.nodes.map((n) => n.note_type))].sort() : []),
    [graphData]
  )

  const toggleRelType = (t: string) => {
    setFilterRelTypes((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })
  }

  const toggleNoteType = (t: string) => {
    setFilterNoteTypes((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })
  }

  const clearFilters = () => {
    setFilterRelTypes(new Set())
    setFilterNoteTypes(new Set())
  }

  const hasFilters = filterRelTypes.size > 0 || filterNoteTypes.size > 0

  // Edges connected to selected node
  const selectedEdges = useMemo(() => {
    if (!selectedNode || !graphData) return []
    return graphData.edges.filter(
      (e) => e.source === selectedNode.path || e.target === selectedNode.path
    )
  }, [selectedNode, graphData])

  // Resolve title for a path
  const titleFor = (path: string) => {
    if (!graphData) return path
    const n = graphData.nodes.find((n) => n.path === path)
    return n?.title ?? path.split('/').pop()?.replace('.md', '') ?? path
  }

  if (loading) {
    return (
      <div className="flex flex-col flex-1 overflow-hidden" data-testid="graph-page">
        <div className="p-4 border-b border-border flex-shrink-0">
          <div className="h-6 w-32 bg-muted animate-pulse rounded" />
          <div className="h-4 w-48 bg-muted animate-pulse rounded mt-2" />
        </div>
        <div className="flex-1 bg-muted/20 animate-pulse" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center" data-testid="graph-page">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center" data-testid="graph-page">
        <p className="text-sm text-muted-foreground">
          No relationships found. Create links between notes to see the graph.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden" data-testid="graph-page">
      {/* Header */}
      <div className="p-4 border-b border-border flex-shrink-0">
        <h1 className="text-xl font-semibold flex items-center">Graph<InfoTip text="Visual map of how your notes connect via links, backlinks, and relationships. Click nodes to inspect, use badges to filter by type." /></h1>
        <p className="text-sm text-muted-foreground mt-1">
          {graphData.nodes.length} nodes, {graphData.edges.length} edges
        </p>

        {/* Filter row */}
        <div className="flex gap-2 mt-3 flex-wrap items-center">
          {relTypes.map((t) => (
            <Badge
              key={`rel-${t}`}
              variant={filterRelTypes.has(t) ? 'default' : 'outline'}
              className="cursor-pointer text-xs"
              onClick={() => toggleRelType(t)}
            >
              {t}
            </Badge>
          ))}
          {relTypes.length > 0 && noteTypes.length > 0 && (
            <span className="text-muted-foreground">|</span>
          )}
          {noteTypes.map((t) => (
            <Badge
              key={`note-${t}`}
              variant={filterNoteTypes.has(t) ? 'default' : 'outline'}
              className="cursor-pointer text-xs"
              onClick={() => toggleNoteType(t)}
            >
              {t}
            </Badge>
          ))}
          {hasFilters && (
            <Button size="sm" variant="ghost" className="text-xs h-6" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </div>
      </div>

      {/* Content: canvas + optional detail panel */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 relative">
          <GraphCanvas
            nodes={graphData.nodes}
            edges={graphData.edges}
            onNodeClick={setSelectedNode}
            selectedNodePath={selectedNode?.path ?? null}
            filterRelTypes={filterRelTypes}
            filterNoteTypes={filterNoteTypes}
          />
        </div>

        {/* Detail panel */}
        {selectedNode && (
          <div className="w-72 border-l border-border bg-card overflow-y-auto flex-shrink-0 p-4">
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold text-foreground leading-tight flex-1 mr-2">
                {selectedNode.title}
              </h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded hover:bg-secondary text-muted-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <Badge variant="secondary" className="text-xs mb-3">
              {selectedNode.note_type}
            </Badge>

            {selectedNode.depth !== undefined && (
              <p className="text-xs text-muted-foreground mb-1">Depth: {selectedNode.depth}</p>
            )}
            {selectedNode.activation !== undefined && (
              <p className="text-xs text-muted-foreground mb-3">
                Activation: {selectedNode.activation.toFixed(2)}
              </p>
            )}

            {/* Connected edges */}
            {selectedEdges.length > 0 && (
              <div className="mt-3">
                <h4 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                  Connections ({selectedEdges.length})
                </h4>
                <ul className="space-y-1.5">
                  {selectedEdges.map((e, i) => {
                    const otherPath =
                      e.source === selectedNode.path ? e.target : e.source
                    return (
                      <li key={i} className="text-sm flex items-center gap-1.5">
                        <Badge variant="outline" className="text-xs px-1 py-0 flex-shrink-0">
                          {e.type}
                        </Badge>
                        <span className="truncate text-foreground">{titleFor(otherPath)}</span>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )}

            <Button
              size="sm"
              className="w-full mt-4"
              onClick={async () => {
                await openNote(selectedNode.path)
                setCurrentView('notes')
              }}
            >
              <FileText className="h-4 w-4 mr-1" />
              Open Note
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
