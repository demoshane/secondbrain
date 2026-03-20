import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Loader2, Sparkles, Check } from 'lucide-react'
import { getAPI } from '@/lib/api'

interface SavedNote {
  title: string
  type: string
  path?: string
  error?: string
}

interface Props {
  open: boolean
  onClose: () => void
}

const TYPE_COLORS: Record<string, string> = {
  meeting: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  person: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  project: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  idea: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  link: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
  note: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
}

export function SmartCaptureModal({ open, onClose }: Props) {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<SavedNote[] | null>(null)

  const handleCapture = async () => {
    if (!content.trim()) return
    setLoading(true)
    try {
      const res = await fetch(`${getAPI()}/smart-capture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      const data = await res.json()
      setResults(data.notes ?? [])
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setContent('')
    setResults(null)
    setLoading(false)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) handleClose() }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Smart Capture
          </DialogTitle>
        </DialogHeader>

        {!results ? (
          <div className="space-y-3">
            <Textarea
              placeholder="Paste meeting notes, conversation dumps, or any freeform text..."
              value={content}
              onChange={e => setContent(e.target.value)}
              rows={8}
              className="resize-y"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={handleClose}>Cancel</Button>
              <Button onClick={handleCapture} disabled={loading || !content.trim()}>
                {loading ? (
                  <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Analyzing...</>
                ) : (
                  <><Sparkles className="h-4 w-4 mr-1" /> Capture</>
                )}
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {results.length} note{results.length !== 1 ? 's' : ''} created:
            </p>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {results.map((note, i) => (
                <div key={i} className="flex items-center gap-2 p-2 rounded border">
                  {note.error ? (
                    <span className="text-sm text-red-500">{note.error}</span>
                  ) : (
                    <>
                      <Check className="h-4 w-4 text-green-500 shrink-0" />
                      <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${TYPE_COLORS[note.type] ?? TYPE_COLORS.note}`}>
                        {note.type}
                      </span>
                      <span className="text-sm truncate">{note.title}</span>
                    </>
                  )}
                </div>
              ))}
            </div>
            <div className="flex justify-end">
              <Button onClick={handleClose}>Done</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
