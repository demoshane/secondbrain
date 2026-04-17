import { useState } from 'react'
import { Merge } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface MergeDialogProps {
  open: boolean
  onClose: () => void
  onMerge: (keepPath: string, discardPath: string) => void
  noteA: { path: string; title: string }
  noteB: { path: string; title: string }
  similarity: number
}

function MergeDialog({ open, onClose, onMerge, noteA, noteB, similarity }: MergeDialogProps) {
  const [selected, setSelected] = useState<'a' | 'b'>('a')

  const keepNote = selected === 'a' ? noteA : noteB
  const discardNote = selected === 'a' ? noteB : noteA

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Merge className="h-5 w-5 shrink-0" />
            Merge duplicate notes
          </DialogTitle>
        </DialogHeader>

        <p className="text-sm text-muted-foreground">
          These notes are {Math.round(similarity * 100)}% similar. Choose which to keep
          — the other note's content will be <strong>merged into it</strong>, not lost.
        </p>

        <div className="space-y-2 pt-1">
          <button
            className={cn(
              'w-full text-left rounded-lg border p-3 transition-colors',
              selected === 'a'
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-muted-foreground/30'
            )}
            onClick={() => setSelected('a')}
          >
            <div className="flex items-center gap-2">
              <div className={cn(
                'h-4 w-4 rounded-full border-2 flex items-center justify-center',
                selected === 'a' ? 'border-primary' : 'border-muted-foreground/40'
              )}>
                {selected === 'a' && <div className="h-2 w-2 rounded-full bg-primary" />}
              </div>
              <span className="font-medium text-sm">{noteA.title}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1 ml-6">{noteA.path}</p>
          </button>

          <button
            className={cn(
              'w-full text-left rounded-lg border p-3 transition-colors',
              selected === 'b'
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-muted-foreground/30'
            )}
            onClick={() => setSelected('b')}
          >
            <div className="flex items-center gap-2">
              <div className={cn(
                'h-4 w-4 rounded-full border-2 flex items-center justify-center',
                selected === 'b' ? 'border-primary' : 'border-muted-foreground/40'
              )}>
                {selected === 'b' && <div className="h-2 w-2 rounded-full bg-primary" />}
              </div>
              <span className="font-medium text-sm">{noteB.title}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1 ml-6">{noteB.path}</p>
          </button>
        </div>

        <p className="text-xs text-muted-foreground pt-1">
          Keep <strong>{keepNote.title}</strong> — content from{' '}
          <strong>{discardNote.title}</strong> will be AI-merged into it. Tags, people,
          and links are preserved from both notes.
        </p>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={() => { onMerge(keepNote.path, discardNote.path); onClose() }}>
            Merge
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export { MergeDialog }
