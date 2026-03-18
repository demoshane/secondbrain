import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useNoteContext } from '@/contexts/NoteContext'
import { useNoteActions } from '@/hooks/useNoteActions'

interface Props {
  open: boolean
  notePath: string
  noteTitle: string
  onClose: () => void
}

export function DeleteNoteModal({ open, notePath, noteTitle, onClose }: Props) {
  const [deleting, setDeleting] = useState(false)
  const { loadNotes } = useNoteContext()
  const { deleteNote } = useNoteActions()

  const handleDelete = async () => {
    setDeleting(true)
    await deleteNote(notePath)
    await loadNotes()
    setDeleting(false)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent data-testid="delete-note-modal">
        <DialogHeader><DialogTitle>Delete Note</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">
          Delete <strong>{noteTitle}</strong>? This cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} data-testid="delete-cancel">Cancel</Button>
          <Button variant="destructive" onClick={handleDelete} disabled={deleting} data-testid="delete-confirm">
            {deleting ? 'Deleting…' : 'Delete'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
