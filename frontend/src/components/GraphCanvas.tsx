import { useRef, useEffect, useCallback, useState } from 'react'
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force'
import type { SimulationNodeDatum, SimulationLinkDatum, Simulation } from 'd3-force'
import { select } from 'd3-selection'
import { zoom } from 'd3-zoom'
import type { GraphNode, GraphEdge } from '@/types'

interface GraphCanvasProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  onNodeClick: (node: GraphNode) => void
  selectedNodePath: string | null
  filterRelTypes: Set<string>
  filterNoteTypes: Set<string>
}

interface D3Node extends SimulationNodeDatum {
  path: string
  title: string
  note_type: string
  connectionCount: number
}

interface D3Link extends SimulationLinkDatum<D3Node> {
  type: string
  strength: number
}

const NODE_COLORS: Record<string, string> = {
  person: 'hsl(210, 80%, 65%)',
  meeting: 'hsl(45, 80%, 65%)',
  project: 'hsl(150, 60%, 55%)',
  link: 'hsl(280, 60%, 65%)',
}
const DEFAULT_NODE_COLOR = 'hsl(0, 0%, 60%)'

const EDGE_COLORS: Record<string, string> = {
  'wiki-link': 'hsl(210, 40%, 50%)',
  backlink: 'hsl(210, 30%, 40%)',
  connection: 'hsl(45, 50%, 50%)',
  similar: 'hsl(0, 0%, 40%)',
  'co-captured': 'hsl(150, 30%, 40%)',
  person: 'hsl(210, 60%, 55%)',
}
const DEFAULT_EDGE_COLOR = 'hsl(0, 0%, 35%)'

function nodeRadius(d: D3Node) {
  return Math.max(5, Math.min(20, 4 + d.connectionCount * 1.5))
}

function truncate(s: string, max: number) {
  return s.length > max ? s.slice(0, max) + '...' : s
}

export function GraphCanvas({
  nodes,
  edges,
  onNodeClick,
  selectedNodePath,
  filterRelTypes,
  filterNoteTypes,
}: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const simRef = useRef<Simulation<D3Node, D3Link> | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

  // Resize observer
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const parent = svg.parentElement
    if (!parent) return

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          setDimensions({ width, height })
        }
      }
    })
    ro.observe(parent)
    // Set initial size
    const rect = parent.getBoundingClientRect()
    if (rect.width > 0) setDimensions({ width: rect.width, height: rect.height })
    return () => ro.disconnect()
  }, [])

  // Build filtered D3 data
  const buildData = useCallback(() => {
    let filteredEdges = edges
    if (filterRelTypes.size > 0) {
      filteredEdges = filteredEdges.filter((e) => filterRelTypes.has(e.type))
    }

    // All nodes are shown; isolates appear as dim dots
    let filteredNodes = nodes
    if (filterNoteTypes.size > 0) {
      filteredNodes = filteredNodes.filter((n) => filterNoteTypes.has(n.note_type))
      // Re-filter edges to only include nodes that survived
      const survivingPaths = new Set(filteredNodes.map((n) => n.path))
      filteredEdges = filteredEdges.filter(
        (e) => survivingPaths.has(e.source) && survivingPaths.has(e.target)
      )
    }

    // Count connections per node
    const connCounts = new Map<string, number>()
    for (const e of filteredEdges) {
      connCounts.set(e.source, (connCounts.get(e.source) ?? 0) + 1)
      connCounts.set(e.target, (connCounts.get(e.target) ?? 0) + 1)
    }

    const d3Nodes: D3Node[] = filteredNodes.map((n) => ({
      path: n.path,
      title: n.title,
      note_type: n.note_type,
      connectionCount: connCounts.get(n.path) ?? 0,
    }))

    const nodeMap = new Map(d3Nodes.map((n) => [n.path, n]))
    const d3Links: D3Link[] = filteredEdges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        source: nodeMap.get(e.source)!,
        target: nodeMap.get(e.target)!,
        type: e.type,
        strength: e.strength,
      }))

    return { d3Nodes, d3Links }
  }, [nodes, edges, filterRelTypes, filterNoteTypes])

  // D3 rendering
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return

    const { width, height } = dimensions
    const { d3Nodes, d3Links } = buildData()

    // Stop existing simulation
    if (simRef.current) simRef.current.stop()

    const svgSel = select(svg)
    svgSel.selectAll('*').remove()

    const g = svgSel.append('g')

    // Zoom
    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 8])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })
    svgSel.call(zoomBehavior)

    // Edges
    const linkSel = g
      .append('g')
      .selectAll('line')
      .data(d3Links)
      .join('line')
      .attr('stroke', (d) => EDGE_COLORS[d.type] ?? DEFAULT_EDGE_COLOR)
      .attr('stroke-width', (d) => Math.max(1, Math.min(3, d.strength * 2)))
      .attr('stroke-opacity', 0.6)

    // Nodes
    const nodeSel = g
      .append('g')
      .selectAll('circle')
      .data(d3Nodes)
      .join('circle')
      .attr('r', nodeRadius)
      .attr('fill', (d) => NODE_COLORS[d.note_type] ?? DEFAULT_NODE_COLOR)
      .attr('fill-opacity', (d) => (d.connectionCount > 0 ? 1 : 0.3))
      .attr('stroke', (d) =>
        d.path === selectedNodePath ? 'hsl(243, 90%, 66%)' : 'hsl(0, 0%, 30%)'
      )
      .attr('stroke-width', (d) => (d.path === selectedNodePath ? 2.5 : 1))
      .attr('stroke-opacity', (d) => (d.connectionCount > 0 ? 1 : 0.25))
      .attr('cursor', 'pointer')
      .on('click', (_event, d) => {
        onNodeClick({
          path: d.path,
          title: d.title,
          note_type: d.note_type,
        })
      })

    // Labels
    const labelSel = g
      .append('g')
      .selectAll('text')
      .data(d3Nodes)
      .join('text')
      .text((d) => truncate(d.title, 20))
      .attr('font-size', 10)
      .attr('fill', 'hsl(0, 0%, 70%)')
      .attr('fill-opacity', (d) => (d.connectionCount > 0 ? 1 : 0.25))
      .attr('text-anchor', 'middle')
      .attr('pointer-events', 'none')

    // Simulation
    const simulation = forceSimulation(d3Nodes)
      .force(
        'link',
        forceLink<D3Node, D3Link>(d3Links)
          .id((d) => d.path)
          .distance(80)
          .strength((link) => (link as D3Link).strength * 0.3)
      )
      .force('charge', forceManyBody().strength(-150))
      .force('center', forceCenter(width / 2, height / 2))
      .force(
        'collide',
        forceCollide<D3Node>().radius((d) => nodeRadius(d) + 4)
      )
      .on('tick', () => {
        linkSel
          .attr('x1', (d) => (d.source as D3Node).x ?? 0)
          .attr('y1', (d) => (d.source as D3Node).y ?? 0)
          .attr('x2', (d) => (d.target as D3Node).x ?? 0)
          .attr('y2', (d) => (d.target as D3Node).y ?? 0)

        nodeSel.attr('cx', (d) => d.x ?? 0).attr('cy', (d) => d.y ?? 0)

        labelSel
          .attr('x', (d) => d.x ?? 0)
          .attr('y', (d) => (d.y ?? 0) + nodeRadius(d) + 12)
      })

    simRef.current = simulation

    return () => {
      simulation.stop()
    }
  }, [dimensions, buildData, selectedNodePath, onNodeClick])

  return (
    <svg
      ref={svgRef}
      width="100%"
      height="100%"
      style={{ display: 'block' }}
      data-testid="graph-canvas"
    />
  )
}
