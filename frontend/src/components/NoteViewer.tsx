import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Edit, Paperclip } from 'lucide-react'
import { useNoteContext } from '@/contexts/NoteContext'
import { useSearchContext } from '@/contexts/SearchContext'
import { useNoteActions } from '@/hooks/useNoteActions'
import { NoteEditor } from './NoteEditor'
import { getAPI } from '@/lib/utils'
import type { Note, Attachment } from '@/types'

interface Props {
  note: Note
}

export function NoteViewer({ note }: Props) {
  const [editing, setEditing] = useState(false)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [localTags, setLocalTags] = useState<string[]>(note.tags ?? [])
  const [editingTag, setEditingTag] = useState<string | null>(null)
  const { setIsDirty } = useNoteContext()
  const { setTagFilter } = useSearchContext()
  const { saveNote } = useNoteActions()

  useEffect(() => {
    setEditing(false)
    setLocalTags(note.tags ?? [])
    setEditingTag(null)
    const encoded = encodeURIComponent(note.path)
    fetch(`${getAPI()}/notes/${encoded}/attachments`)
      .then(r => r.json())
      .then(d => setAttachments(d.attachments ?? []))
      .catch(() => setAttachments([]))
  }, [note.path])

  if (editing) {
    return (
      <NoteEditor
        note={note}
        onClose={() => { setEditing(false); setIsDirty(false) }}
      />
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden" data-testid="note-viewer">
      <div className="flex items-center justify-between px-4 py-2 border-b">
        <h1 className="text-lg font-semibold truncate" data-testid="note-title">{note.title}</h1>
        <Button size="sm" variant="ghost" onClick={() => setEditing(true)} data-testid="edit-btn">
          <Edit className="h-4 w-4" />
        </Button>
      </div>
      {localTags.length > 0 && (
        <div className="flex flex-wrap gap-1 px-4 py-1 border-b" data-testid="tag-chips">
          {localTags.map(tag => (
            editingTag === tag ? (
              <input
                key={tag}
                className="tag-chip-input text-xs border rounded px-1"
                autoFocus
                defaultValue={tag}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const newTag = (e.target as HTMLInputElement).value.trim()
                    const newTags = newTag && newTag !== tag
                      ? localTags.map(t => t === tag ? newTag : t)
                      : localTags
                    setLocalTags(newTags)
                    setEditingTag(null)
                    const content = `---\ntitle: ${note.title}\ntags: ${JSON.stringify(newTags)}\ntype: ${note.type}\n---\n\n${note.body ?? ''}\n`
                    saveNote(note.path, content)
                  } else if (e.key === 'Escape') {
                    setEditingTag(null)
                  }
                }}
              />
            ) : (
              <Badge
                key={tag}
                variant="secondary"
                className="cursor-pointer hover:bg-accent"
                data-testid={`tag-${tag}`}
                onClick={() => setTagFilter(tag)}
                onDoubleClick={() => setEditingTag(tag)}
              >
                {tag}
              </Badge>
            )
          ))}
        </div>
      )}
      <div className="flex-1 overflow-auto px-4 py-3 prose prose-sm dark:prose-invert max-w-none" data-testid="note-body">
        <Markdown remarkPlugins={[remarkGfm]}>{note.body ?? ''}</Markdown>
      </div>
      {attachments.length > 0 && (
        <div className="px-4 py-2 border-t" data-testid="attachment-list">
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
    </div>
  )
}
