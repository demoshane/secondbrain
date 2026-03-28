import { useRef, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Loader2, Brain, FileText } from 'lucide-react'
import { getAPI } from '@/lib/utils'
import { useNoteContext } from '@/contexts/NoteContext'
import { useUIContext } from '@/contexts/UIContext'

interface Source {
  title: string
  path: string
  snippet: string
}

interface Props {
  open: boolean
  onClose: () => void
}

export function AskBrainModal({ open, onClose }: Props) {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [answer, setAnswer] = useState<string | null>(null)
  const [sources, setSources] = useState<Source[]>([])
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { openNote } = useNoteContext()
  const { setCurrentView } = useUIContext()

  const handleAsk = async () => {
    if (!question.trim() || loading) return
    setLoading(true)
    setAnswer(null)
    setSources([])
    setError(null)
    try {
      const res = await fetch(`${getAPI()}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'Request failed')
        return
      }
      setAnswer(data.answer)
      setSources(data.sources || [])
    } catch {
      setError('Could not reach the brain API.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleAsk()
  }

  const handleOpenNote = async (path: string) => {
    setCurrentView('notes')
    await openNote(path)
    onClose()
  }

  const handleClose = () => {
    setQuestion('')
    setAnswer(null)
    setSources([])
    setError(null)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) handleClose() }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-4 w-4 text-violet-400" />
            Ask Brain
          </DialogTitle>
        </DialogHeader>
        <div className="flex gap-2 mt-1">
          <Input
            ref={inputRef}
            autoFocus
            placeholder="What do you remember about… / What meetings do I have upcoming…"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            className="flex-1"
          />
          <Button onClick={handleAsk} disabled={!question.trim() || loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Ask'}
          </Button>
        </div>

        {error && (
          <p className="text-sm text-destructive mt-2">{error}</p>
        )}

        {answer && (
          <div className="mt-4 space-y-4">
            <div className="rounded-md bg-muted/50 p-4 text-sm leading-relaxed whitespace-pre-wrap">
              {answer}
            </div>
            {sources.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Sources</p>
                <div className="space-y-1">
                  {sources.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => handleOpenNote(s.path)}
                      className="w-full text-left rounded px-3 py-2 hover:bg-muted transition-colors flex items-start gap-2"
                    >
                      <FileText className="h-3.5 w-3.5 mt-0.5 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{s.title}</p>
                        {s.snippet && (
                          <p className="text-xs text-muted-foreground line-clamp-2">{s.snippet}</p>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
