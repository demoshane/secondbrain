import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Eye, EyeOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useNoteContext } from '@/contexts/NoteContext'
import { useNoteActions } from '@/hooks/useNoteActions'
import { toast } from 'sonner'
import type { Note } from '@/types'

interface Props {
  note: Note
  onClose: () => void
}

export function NoteEditor({ note, onClose }: Props) {
  const [title, setTitle] = useState(note.title ?? '')
  const [content, setContent] = useState(note.body ?? '')
  const [saving, setSaving] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const { openNote, setIsDirty } = useNoteContext()
  const { saveNote } = useNoteActions()

  const handleSave = async () => {
    setSaving(true)
    const ok = await saveNote(note.path, content)
    setSaving(false)
    if (ok) {
      toast.success('Note saved')
      await openNote(note.path)
      onClose()
    } else {
      toast.error('Save failed. Your changes are preserved — try again.')
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-background" data-testid="note-editor">
      {/* Title input */}
      <input
        className="text-xl font-semibold bg-transparent border-none outline-none text-foreground w-full mb-4"
        value={title}
        onChange={e => { setTitle(e.target.value); setIsDirty(true) }}
        placeholder="Note title"
        data-testid="editor-title"
      />
      {/* Preview/Edit toggle bar */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-muted-foreground">{previewing ? 'Preview' : 'Editing'}</span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setPreviewing(p => !p)}
        >
          {previewing ? <EyeOff className="h-4 w-4 mr-1" /> : <Eye className="h-4 w-4 mr-1" />}
          {previewing ? 'Edit' : 'Preview'}
        </Button>
      </div>
      {/* Body: textarea in edit mode, rendered markdown in preview mode */}
      {previewing ? (
        <div
          className="flex-1 w-full bg-card border border-border rounded p-3 text-sm text-foreground min-h-[300px] overflow-y-auto [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:mt-4 [&_h1]:mb-2 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-3 [&_h2]:mb-1 [&_a]:text-primary [&_a]:underline [&_code]:bg-muted [&_code]:px-1 [&_code]:rounded [&_pre]:bg-muted [&_pre]:p-3 [&_pre]:rounded [&_ul]:list-disc [&_ul]:ml-4 [&_ol]:list-decimal [&_ol]:ml-4 [&_blockquote]:border-l-2 [&_blockquote]:border-primary [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content || '*Nothing to preview*'}</ReactMarkdown>
        </div>
      ) : (
        <textarea
          className="flex-1 w-full bg-input border border-border rounded p-3 text-sm text-foreground font-mono resize-none min-h-[300px]"
          value={content}
          onChange={e => { setContent(e.target.value); setIsDirty(true) }}
          placeholder="Write your note in Markdown..."
          data-testid="editor-body"
        />
      )}
      {/* Bottom bar */}
      <div className="flex items-center gap-2 mt-4">
        <Button
          variant="default"
          onClick={handleSave}
          disabled={saving}
          data-testid="editor-save"
        >
          {saving ? 'Saving…' : 'Save Note'}
        </Button>
        <Button
          variant="ghost"
          onClick={onClose}
          data-testid="editor-cancel"
        >
          Cancel
        </Button>
      </div>
    </div>
  )
}
