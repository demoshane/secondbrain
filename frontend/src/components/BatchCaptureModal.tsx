import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { getAPI } from '@/lib/utils'

interface Props {
  open: boolean
  onClose: () => void
}

export function BatchCaptureModal({ open, onClose }: Props) {
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<{ succeeded: string[]; failed: string[] } | null>(null)

  const handleRun = async () => {
    setRunning(true)
    try {
      const res = await fetch(`${getAPI()}/capture/batch`, { method: 'POST' })
      const data = await res.json()
      setResult(data)
    } catch {
      setResult({ succeeded: [], failed: ['Network error'] })
    }
    setRunning(false)
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent data-testid="batch-capture-modal">
        <DialogHeader><DialogTitle>Batch Capture</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">
          Scan the brain directory and index all untracked markdown files.
        </p>
        {result && (
          <div className="text-sm space-y-1">
            <p className="text-green-600">{result.succeeded.length} captured</p>
            {result.failed.length > 0 && <p className="text-red-500">{result.failed.length} failed</p>}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Close</Button>
          <Button onClick={handleRun} disabled={running} data-testid="batch-capture-submit">
            {running ? 'Running…' : 'Run Batch Capture'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
