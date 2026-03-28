import { useState } from 'react'
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
      {/* Body textarea */}
      <textarea
        className="flex-1 w-full bg-input border border-border rounded p-3 text-sm text-foreground font-mono resize-none min-h-[300px]"
        value={content}
        onChange={e => { setContent(e.target.value); setIsDirty(true) }}
        placeholder="Write your note in Markdown..."
        data-testid="editor-body"
      />
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
