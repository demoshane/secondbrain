import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useNoteContext } from '@/contexts/NoteContext'
import { useNoteActions } from '@/hooks/useNoteActions'
import { getAPI, encodePath } from '@/lib/utils'

interface Impact {
  action_items: number
  relationships: number
  appears_in_people_of: number
}

interface Props {
  open: boolean
  notePath: string
  noteTitle: string
  onClose: () => void
}

export function DeleteNoteModal({ open, notePath, noteTitle, onClose }: Props) {
  const [deleting, setDeleting] = useState(false)
  const [impact, setImpact] = useState<Impact | null>(null)
  const [loadingImpact, setLoadingImpact] = useState(false)
  const { loadNotes } = useNoteContext()
  const { deleteNote } = useNoteActions()

  useEffect(() => {
    if (!open) { setImpact(null); return }
    setLoadingImpact(true)
    fetch(`${getAPI()}/notes/${encodePath(notePath)}/impact`)
      .then(r => r.json())
      .then((d: Impact) => setImpact(d))
      .catch(() => setImpact(null))
      .finally(() => setLoadingImpact(false))
  }, [open, notePath])

  const handleDelete = async () => {
    setDeleting(true)
    await deleteNote(notePath)
    await loadNotes()
    setDeleting(false)
    onClose()
  }

  const hasImpact = impact && (impact.action_items > 0 || impact.relationships > 0 || impact.appears_in_people_of > 0)

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent data-testid="delete-note-modal">
        <DialogHeader><DialogTitle>Delete Note</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">
          Delete <strong>{noteTitle}</strong>? This cannot be undone.
        </p>
        {loadingImpact && (
          <div className="animate-pulse bg-muted rounded h-8 my-2" />
        )}
        {!loadingImpact && hasImpact && (
          <div className="rounded border border-border p-2 my-2">
            <p className="text-xs font-semibold text-muted-foreground mb-1">Impact</p>
            <p className="text-xs text-muted-foreground">
              Action items: {impact.action_items} · Relationships: {impact.relationships} · Mentioned in: {impact.appears_in_people_of} notes
            </p>
          </div>
        )}
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
