import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, Plus, Trash2 } from 'lucide-react'
import { cn, getAPI, encodePath } from '@/lib/utils'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { useUIContext } from '@/contexts/UIContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { NewEntityModal } from './NewEntityModal'
import { DeleteEntityModal } from './DeleteEntityModal'
import type { ProjectSummary, ActionItem } from '@/types'

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

export function ProjectsPage() {
  const { setCurrentView } = useUIContext()
  const { openNote } = useNoteContext()

  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [filter, setFilter] = useState('')
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [showNewEntity, setShowNewEntity] = useState(false)
  const [showDeleteEntity, setShowDeleteEntity] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ name: string; path: string } | null>(null)
  const [projectDetail, setProjectDetail] = useState<{
    body: string
    title: string
    updated_at: string
    open_actions: number
  } | null>(null)
  const [backlinks, setBacklinks] = useState<{ path: string; title: string }[]>([])
  const [actions, setActions] = useState<ActionItem[]>([])

  const loadProjects = () => {
    fetch(`${getAPI()}/projects`)
      .then(r => r.json())
      .then(d => setProjects(d.projects ?? []))
      .catch(() => {})
  }

  // Fetch projects list on mount
  useEffect(() => {
    loadProjects()
  }, [])

  // Fetch project detail on selectedPath change
  useEffect(() => {
    if (!selectedPath) return
    const enc = encodePath(selectedPath)
    Promise.all([
      fetch(`${getAPI()}/projects/${enc}`).then(r => r.json()),
      fetch(`${getAPI()}/notes/${enc}/meta`).then(r => r.json()),
      fetch(`${getAPI()}/actions?note_path=${enc}`).then(r => r.json()),
    ]).then(([detail, meta, acts]) => {
      setProjectDetail({
        body: detail.body ?? '',
        title: detail.title ?? '',
        updated_at: detail.updated_at ?? '',
        open_actions: detail.open_actions ?? 0,
      })
      setBacklinks(meta.backlinks ?? [])
      setActions(acts.actions ?? [])
    }).catch(() => {})
  }, [selectedPath])

  async function handleOpenInNotes() {
    if (!selectedPath) return
    await openNote(selectedPath)
    setCurrentView('notes')
  }

  const filtered = projects.filter(p =>
    p.title.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="flex h-full" data-testid="projects-page">
      {/* Left column — project list */}
      <div className="w-80 border-r overflow-y-auto flex flex-col">
        <div className="p-2 border-b flex gap-2">
          <input
            placeholder="Filter by title..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="flex-1 rounded-md border border-input bg-background px-3 py-1 text-sm outline-none focus:ring-1 focus:ring-ring"
          />
          <Button
            size="sm"
            onClick={() => setShowNewEntity(true)}
            data-testid="new-project-button"
          >
            <Plus size={16} className="mr-1" /> New Project
          </Button>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead className="w-24">Updated</TableHead>
              <TableHead className="w-16 text-right">Actions</TableHead>
              <TableHead className="w-8" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map(p => (
              <TableRow
                key={p.path}
                className={cn('cursor-pointer', selectedPath === p.path && 'bg-accent')}
                onClick={() => setSelectedPath(p.path)}
              >
                <TableCell className="font-medium">{p.title}</TableCell>
                <TableCell className="text-muted-foreground">{p.updated_at}</TableCell>
                <TableCell className="text-right">{p.open_actions}</TableCell>
                <TableCell>
                  <button
                    className="opacity-0 group-hover:opacity-100 hover:text-destructive p-1 rounded"
                    onClick={e => {
                      e.stopPropagation()
                      setDeleteTarget({ name: p.title, path: p.path })
                      setShowDeleteEntity(true)
                    }}
                    data-testid="delete-project-button"
                    title={`Delete ${p.title}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground py-4">
                  No projects found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Right column — detail panel */}
      <div className="flex-1 overflow-y-auto">
        {!selectedPath ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            Select a project to view details
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <h2 className="text-lg font-semibold">{projectDetail?.title ?? ''}</h2>
              <Button size="sm" variant="outline" onClick={handleOpenInNotes}>
                Open in Notes
              </Button>
            </div>

            <Section title="Note" count={projectDetail?.body ? 1 : 0}>
              <div className="prose prose-sm dark:prose-invert max-w-none py-2">
                <Markdown remarkPlugins={[remarkGfm]}>{projectDetail?.body ?? ''}</Markdown>
              </div>
            </Section>

            <Section title="Action Items" count={actions.filter(a => !a.done).length}>
              <div data-testid="project-actions-section">
                {actions.filter(a => !a.done).length === 0 ? (
                  <p className="text-sm text-muted-foreground py-1">No open actions</p>
                ) : (
                  <ul className="space-y-1">
                    {actions.filter(a => !a.done).map(a => (
                      <li key={a.id} className="flex items-start gap-2 text-sm">
                        <input type="checkbox" disabled checked={a.done} className="mt-0.5" />
                        <span>
                          {a.text}
                          {a.due_date && (
                            <span className="ml-2 text-muted-foreground">{a.due_date}</span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Section>

            <Section title="Related Notes" count={backlinks.length}>
              <div data-testid="project-backlinks-section">
                {backlinks.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-1">No related notes</p>
                ) : (
                  <ul className="space-y-1">
                    {backlinks.map(b => (
                      <li key={b.path} className="text-sm">{b.title}</li>
                    ))}
                  </ul>
                )}
              </div>
            </Section>
          </div>
        )}
      </div>

      <NewEntityModal
        open={showNewEntity}
        onClose={() => setShowNewEntity(false)}
        entityType="projects"
        onCreated={loadProjects}
      />
      {deleteTarget && (
        <DeleteEntityModal
          open={showDeleteEntity}
          onClose={() => { setShowDeleteEntity(false); setDeleteTarget(null) }}
          entityType="projects"
          entityName={deleteTarget.name}
          entityPath={deleteTarget.path}
          onDeleted={() => {
            loadProjects()
            if (selectedPath === deleteTarget.path) setSelectedPath(null)
          }}
        />
      )}
    </div>
  )
}
