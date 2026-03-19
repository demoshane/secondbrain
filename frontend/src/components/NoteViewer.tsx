import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Edit, Paperclip, Plus, X } from 'lucide-react'
import { useNoteContext } from '@/contexts/NoteContext'
import { useSearchContext } from '@/contexts/SearchContext'
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
  const [addingTag, setAddingTag] = useState(false)
  const { setIsDirty } = useNoteContext()
  const { setTagFilter } = useSearchContext()

  const saveTagsFieldLevel = (newTags: string[]) => {
    fetch(`${getAPI()}/notes/${encodeURIComponent(note.path)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tags: newTags }),
    }).catch(() => {})
  }

  useEffect(() => {
    setEditing(false)
    setLocalTags(note.tags ?? [])
    setEditingTag(null)
    setAddingTag(false)
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
      <div className="flex flex-wrap gap-1 items-center px-4 py-1 border-b" data-testid="tag-chips">
        {localTags.map(tag => (
          editingTag === tag ? (
            <input
              key={tag}
              className="tag-chip-input text-xs border rounded px-1 w-20 bg-background text-foreground"
              autoFocus
              defaultValue={tag}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const newTag = (e.target as HTMLInputElement).value.trim()
                  if (newTag && newTag !== tag) {
                    const newTags = localTags.map(t => t === tag ? newTag : t)
                    setLocalTags(newTags)
                    saveTagsFieldLevel(newTags)
                  }
                  setEditingTag(null)
                } else if (e.key === 'Escape') {
                  setEditingTag(null)
                }
              }}
              onBlur={() => setEditingTag(null)}
            />
          ) : (
            <Badge
              key={tag}
              variant="secondary"
              className="cursor-pointer hover:bg-accent group"
              data-testid={`tag-${tag}`}
              onClick={() => setTagFilter(tag)}
              onDoubleClick={() => setEditingTag(tag)}
            >
              {tag}
              <button
                className="ml-1 opacity-0 group-hover:opacity-100 hover:text-destructive"
                onClick={e => {
                  e.stopPropagation()
                  const newTags = localTags.filter(t => t !== tag)
                  setLocalTags(newTags)
                  saveTagsFieldLevel(newTags)
                }}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )
        ))}
        {addingTag ? (
          <input
            className="text-xs border rounded px-1 w-20 bg-background text-foreground"
            autoFocus
            placeholder="new tag"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const val = (e.target as HTMLInputElement).value.trim()
                if (val && !localTags.includes(val)) {
                  const newTags = [...localTags, val]
                  setLocalTags(newTags)
                  saveTagsFieldLevel(newTags)
                }
                setAddingTag(false)
              } else if (e.key === 'Escape') {
                setAddingTag(false)
              }
            }}
            onBlur={() => setAddingTag(false)}
          />
        ) : (
          <button
            className="text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setAddingTag(true)}
          >
            <Plus className="h-3 w-3" />
          </button>
        )}
      </div>
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
