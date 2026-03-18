import { useState, useRef } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useNoteContext } from '@/contexts/NoteContext'
import { getAPI } from '@/lib/utils'

interface Props {
  open: boolean
  onClose: () => void
}

export function FileUploadModal({ open, onClose }: Props) {
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<string>('')
  const fileRef = useRef<HTMLInputElement>(null)
  const { currentPath, openNote } = useNoteContext()

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0]
    if (!file || !currentPath) return
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    const encoded = encodeURIComponent(currentPath)
    const res = await fetch(`${getAPI()}/notes/${encoded}/files`, { method: 'POST', body: form })
    setUploading(false)
    if (res.ok) {
      await openNote(currentPath)
      setResult('Uploaded successfully')
    } else {
      setResult('Upload failed')
    }
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent data-testid="file-upload-modal">
        <DialogHeader><DialogTitle>Upload File</DialogTitle></DialogHeader>
        <input type="file" ref={fileRef} data-testid="file-input" />
        {result && <p className="text-sm text-muted-foreground">{result}</p>}
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
