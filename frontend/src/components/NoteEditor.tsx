import { useState } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { markdown } from '@codemirror/lang-markdown'
import { oneDark } from '@codemirror/theme-one-dark'
import { Button } from '@/components/ui/button'
import { useNoteContext } from '@/contexts/NoteContext'
import { useNoteActions } from '@/hooks/useNoteActions'
import type { Note } from '@/types'

interface Props {
  note: Note
  onClose: () => void
}

export function NoteEditor({ note, onClose }: Props) {
  const [content, setContent] = useState(note.body ?? '')
  const [saving, setSaving] = useState(false)
  const { openNote, setIsDirty } = useNoteContext()
  const { saveNote } = useNoteActions()

  const isDarkMode = document.documentElement.classList.contains('dark')

  const handleSave = async () => {
    setSaving(true)
    const ok = await saveNote(note.path, content)
    setSaving(false)
    if (ok) {
      await openNote(note.path)
      onClose()
    }
  }

  return (
    <div className="flex flex-col h-full" data-testid="note-editor">
      <div className="flex items-center gap-2 px-4 py-2 border-b">
        <span className="flex-1 font-semibold truncate">{note.title}</span>
        <Button size="sm" variant="outline" onClick={onClose} data-testid="editor-cancel">Cancel</Button>
        <Button size="sm" onClick={handleSave} disabled={saving} data-testid="editor-save">
          {saving ? 'Saving…' : 'Save'}
        </Button>
      </div>
      <div className="flex-1 overflow-hidden">
        <CodeMirror
          value={content}
          extensions={[markdown()]}
          theme={isDarkMode ? oneDark : 'light'}
          onChange={(val) => { setContent(val); setIsDirty(true) }}
          height="100%"
          basicSetup={{ lineNumbers: false, foldGutter: false }}
        />
      </div>
    </div>
  )
}
