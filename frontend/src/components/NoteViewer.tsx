import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Pencil, Upload, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { NoteTypeBadge } from '@/components/ui/note-type-badge'
import { TagBadge } from '@/components/ui/tag-badge'
import { PersonBadge } from '@/components/ui/person-badge'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { AttachmentsSection } from '@/components/ui/attachments-section'
import { FileUploadModal } from './FileUploadModal'
import { NoteEditor } from './NoteEditor'
import { useNoteContext } from '@/contexts/NoteContext'
import { useSearchContext } from '@/contexts/SearchContext'
import { useUIContext } from '@/contexts/UIContext'
import { getAPI, encodePath } from '@/lib/utils'
import { toast } from 'sonner'
import type { Note } from '@/types'
import type { Components } from 'react-markdown'

interface Props {
  note: Note
}

function relativeTime(dateStr: string): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} day${days !== 1 ? 's' : ''} ago`
  const weeks = Math.floor(days / 7)
  if (weeks < 5) return `${weeks} week${weeks !== 1 ? 's' : ''} ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months} month${months !== 1 ? 's' : ''} ago`
  return `${Math.floor(months / 12)} year${Math.floor(months / 12) !== 1 ? 's' : ''} ago`
}

// Pre-process body: replace [[Title]] with [Title](wiki:Title%20encoded) so
// ReactMarkdown treats them as links that the custom renderer can intercept.
function preprocessWikiLinks(body: string): string {
  return body.replace(/\[\[([^\]]+)\]\]/g, (_match, title: string) => {
    const encoded = encodeURIComponent(title)
    return `[${title}](wiki:${encoded})`
  })
}

export function NoteViewer({ note }: Props) {
  const [editing, setEditing] = useState(false)
  const [refreshTick, setRefreshTick] = useState(0)
  const [showDelete, setShowDelete] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')
  const titleEscaped = useRef(false)
  const { notes, loadNotes, setIsDirty, openNote } = useNoteContext()
  const { setTagFilter } = useSearchContext()
  const { setCurrentView } = useUIContext()

  // Build a case-insensitive title → path map from all loaded notes.
  // Recomputed only when the notes list changes (stable reference).
  const titleToPath = useCallback(() => {
    const map = new Map<string, string>()
    for (const n of notes) {
      map.set(n.title.toLowerCase(), n.path)
    }
    return map
  }, [notes])

  // Custom ReactMarkdown link renderer — intercepts wiki: scheme links.
  const markdownComponents: Components = {
    a({ href, children }) {
      if (href?.startsWith('wiki:')) {
        const title = decodeURIComponent(href.slice(5))
        const map = titleToPath()
        const targetPath = map.get(title.toLowerCase())
        if (targetPath) {
          return (
            <button
              className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors cursor-pointer"
              onClick={() => {
                setCurrentView('notes')
                openNote(targetPath)
              }}
              title={`Go to: ${title}`}
            >
              {children}
            </button>
          )
        }
        // No matching note — render as dimmed non-interactive text
        return (
          <span
            className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground opacity-50"
            title={`No note found: ${title}`}
          >
            {children}
          </span>
        )
      }
      // Regular link — render normally
      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      )
    },
  }

  useEffect(() => {
    setEditing(false)
    setShowDelete(false)
    setRefreshTick(0)
  }, [note.path])

  const handleDelete = async () => {
    try {
      const res = await fetch(`${getAPI()}/notes/${encodePath(note.path)}`, { method: 'DELETE' })
      if (res.ok) {
        toast.success('Note deleted')
        await loadNotes()
      } else {
        toast.error('Delete failed. Try again or check the app logs.')
      }
    } catch {
      toast.error('Delete failed. Try again or check the app logs.')
    }
  }

  const handleTitleBlur = async () => {
    if (titleEscaped.current) {
      titleEscaped.current = false
      return
    }
    setEditingTitle(false)
    const newTitle = titleDraft.trim()
    if (!newTitle || newTitle === note.title) return
    try {
      const res = await fetch(`${getAPI()}/notes/${encodePath(note.path)}/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle }),
      })
      if (res.ok) {
        const data = await res.json()
        toast.success('Title updated')
        await loadNotes()
        await openNote(data.renamed_file ? data.new_path : note.path)
      } else {
        toast.error('Failed to update title')
      }
    } catch {
      toast.error('Failed to update title')
    }
  }

  const handleTitleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.currentTarget.blur()
    } else if (e.key === 'Escape') {
      titleEscaped.current = true
      setEditingTitle(false)
    }
  }

  if (editing) {
    return (
      <NoteEditor
        note={note}
        onClose={() => { setEditing(false); setIsDirty(false) }}
      />
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-background" data-testid="note-viewer">
      {/* Title — click pencil to edit inline */}
      <div className="flex items-center gap-2 mb-1 group/title">
        {editingTitle ? (
          <input
            autoFocus
            className="text-xl font-semibold text-foreground bg-transparent border-b border-primary outline-none w-full"
            value={titleDraft}
            onChange={e => setTitleDraft(e.target.value)}
            onKeyDown={handleTitleKeyDown}
            onBlur={handleTitleBlur}
            data-testid="title-input"
          />
        ) : (
          <>
            <h1 className="text-xl font-semibold text-foreground" data-testid="note-title">
              {note.title}
            </h1>
            <button
              className="opacity-0 group-hover/title:opacity-100 text-muted-foreground hover:text-foreground transition-opacity shrink-0"
              onClick={() => { setTitleDraft(note.title); setEditingTitle(true) }}
              title="Edit title"
              data-testid="edit-title-btn"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
          </>
        )}
      </div>

      {/* Metadata row */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4">
        <NoteTypeBadge type={note.type || 'note'} />
        {note.updated_at && (
          <span title={note.updated_at}>{relativeTime(note.updated_at)}</span>
        )}
        {note.created_at && (
          <span title={note.created_at}>Created {relativeTime(note.created_at)}</span>
        )}
      </div>

      {/* Tags row */}
      {note.tags && note.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {note.tags.map(tag => (
            <TagBadge
              key={tag}
              tag={tag}
              onClick={() => setTagFilter(tag)}
            />
          ))}
        </div>
      )}

      {/* People row */}
      {note.people && note.people.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {note.people.map(personPath => (
            <PersonBadge
              key={personPath}
              name={personPath.split('/').pop()?.replace('.md', '').replace(/-/g, ' ') ?? personPath}
              path={personPath}
            />
          ))}
        </div>
      )}

      {/* Action bar */}
      <div className="flex items-center gap-1 mb-4 border-b border-border pb-3 group">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setEditing(true)}
          data-testid="edit-btn"
        >
          <Pencil className="h-4 w-4 mr-1" />
          Edit Note
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setShowUpload(true)}>
          <Upload className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-destructive opacity-0 group-hover:opacity-100"
          onClick={() => setShowDelete(true)}
          data-testid="delete-btn"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Markdown body */}
      <div
        className="text-sm leading-relaxed text-foreground [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:mt-4 [&_h1]:mb-2 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-3 [&_h2]:mb-1 [&_a]:text-primary [&_a]:underline [&_code]:bg-muted [&_code]:px-1 [&_code]:rounded [&_pre]:bg-muted [&_pre]:p-3 [&_pre]:rounded [&_ul]:list-disc [&_ul]:ml-4 [&_ol]:list-decimal [&_ol]:ml-4 [&_blockquote]:border-l-2 [&_blockquote]:border-primary [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground"
        data-testid="note-body"
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {preprocessWikiLinks(note.body ?? '')}
        </ReactMarkdown>
      </div>

      <AttachmentsSection
        notePath={note.path}
        refreshTick={refreshTick}
      />

      <FileUploadModal
        open={showUpload}
        onClose={() => setShowUpload(false)}
        onUploaded={() => setRefreshTick(t => t + 1)}
      />

      {/* Delete confirmation */}
      <ConfirmDialog
        open={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title={`Delete '${note.title}'?`}
        description="This cannot be undone. Backlinks, attachments, and action items will also be removed."
        confirmLabel="Delete Note"
        cancelLabel="Keep Note"
        variant="destructive"
      />
    </div>
  )
}
