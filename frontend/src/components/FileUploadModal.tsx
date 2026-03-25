import { useState, useRef } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useNoteContext } from '@/contexts/NoteContext'
import { getAPI } from '@/lib/utils'
import { toast } from 'sonner'

interface Props {
  open: boolean
  onClose: () => void
}

export function FileUploadModal({ open, onClose }: Props) {
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const { currentPath, openNote } = useNoteContext()

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0]
    if (!file || !currentPath) return
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    form.append('note_path', currentPath)
    const res = await fetch(`${getAPI()}/files/upload`, { method: 'POST', body: form })
    setUploading(false)
    if (res.ok) {
      await openNote(currentPath)
      toast.success('File uploaded')
      onClose()
    } else {
      const err = await res.json().catch(() => ({}))
      toast.error(err.error ?? 'Upload failed')
    }
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent data-testid="file-upload-modal">
        <DialogHeader><DialogTitle>Upload File</DialogTitle></DialogHeader>
        <input type="file" ref={fileRef} data-testid="file-input" />
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleUpload} disabled={uploading} data-testid="upload-submit">
            {uploading ? 'Uploading…' : 'Upload'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
