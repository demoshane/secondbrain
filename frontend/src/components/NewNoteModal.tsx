import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useNoteContext } from '@/contexts/NoteContext'
import { useNoteActions } from '@/hooks/useNoteActions'

const NOTE_TYPES = ['note', 'idea', 'meeting', 'person', 'project', 'strategy']

interface Props {
  open: boolean
  onClose: () => void
}

export function NewNoteModal({ open, onClose }: Props) {
  const [title, setTitle] = useState('')
  const [type, setType] = useState('note')
  const [creating, setCreating] = useState(false)
  const { loadNotes, openNote } = useNoteContext()
  const { createNote } = useNoteActions()

  const handleCreate = async () => {
    if (!title.trim()) return
    setCreating(true)
    const result = await createNote(title, type)
    setCreating(false)
    if (result?.path) {
      await loadNotes()
      await openNote(result.path)
    }
    setTitle('')
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent data-testid="new-note-modal">
        <DialogHeader><DialogTitle>New Note</DialogTitle></DialogHeader>
        <Input
          placeholder="Title"
          value={title}
          onChange={e => setTitle(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleCreate()}
          data-testid="new-note-title"
        />
        <Select value={type} onValueChange={setType}>
          <SelectTrigger data-testid="new-note-type"><SelectValue /></SelectTrigger>
          <SelectContent>
            {NOTE_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
          </SelectContent>
        </Select>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleCreate} disabled={creating || !title.trim()} data-testid="new-note-submit">
            {creating ? 'Creating…' : 'Create'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
