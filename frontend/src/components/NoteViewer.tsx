import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Pencil, Upload, Trash2, Paperclip } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { NoteTypeBadge } from '@/components/ui/note-type-badge'
import { TagBadge } from '@/components/ui/tag-badge'
import { PersonBadge } from '@/components/ui/person-badge'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { FileUploadModal } from './FileUploadModal'
import { NoteEditor } from './NoteEditor'
import { useNoteContext } from '@/contexts/NoteContext'
import { useSearchContext } from '@/contexts/SearchContext'
import { getAPI, encodePath } from '@/lib/utils'
import { toast } from 'sonner'
import type { Note, Attachment } from '@/types'

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

export function NoteViewer({ note }: Props) {
  const [editing, setEditing] = useState(false)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [showDelete, setShowDelete] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const { loadNotes, setIsDirty } = useNoteContext()
  const { setTagFilter } = useSearchContext()

  useEffect(() => {
    setEditing(false)
    setShowDelete(false)
    fetch(`${getAPI()}/notes/attachments?path=${encodeURIComponent(note.path)}`)
      .then(r => r.json())
      .then(d => setAttachments(d.attachments ?? []))
      .catch(() => setAttachments([]))
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
      {/* Title */}
      <h1 className="text-xl font-semibold text-foreground mb-1" data-testid="note-title">
        {note.title}
      </h1>

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
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {note.body ?? ''}
        </ReactMarkdown>
      </div>

      {/* Attachments section */}
      {attachments.length > 0 && (
        <div className="mt-4 pt-3 border-t border-border" data-testid="attachment-list">
          <div className="flex items-center gap-1 mb-1 text-xs font-semibold uppercase text-muted-foreground">
            <Paperclip className="h-3 w-3" />
            Attachments
          </div>
          <ul className="space-y-0.5">
            {attachments.map(a => (
              <li key={a.filename} className="text-xs text-muted-foreground truncate">
                <a href={a.file_path} target="_blank" rel="noreferrer" className="hover:text-foreground hover:underline">
                  {a.filename}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <FileUploadModal open={showUpload} onClose={() => setShowUpload(false)} />

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
