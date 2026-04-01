import { useRef, useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Loader2, Brain, FileText, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'
import { getAPI } from '@/lib/utils'
import { useNoteContext } from '@/contexts/NoteContext'
import { useUIContext } from '@/contexts/UIContext'

interface Source {
  title: string
  path: string
  snippet: string
}

interface Exchange {
  question: string
  answer: string
  sources: Source[]
}

interface Props {
  open: boolean
  onClose: () => void
}

export function AskBrainModal({ open, onClose }: Props) {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const { openNote } = useNoteContext()
  const { setCurrentView } = useUIContext()

  // Auto-scroll to bottom when new exchange arrives
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [exchanges, loading])

  const handleAsk = async () => {
    if (!question.trim() || loading) return
    const q = question.trim()
    setLoading(true)
    setError(null)
    setQuestion('')
    try {
      const history = exchanges.map(e => ({
        question: e.question,
        answer: e.answer,
        source_paths: e.sources.map(s => s.path),
      }))
      const res = await fetch(`${getAPI()}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, history }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'Request failed')
        setQuestion(q) // restore question so user can retry
        return
      }
      setExchanges(prev => [...prev, {
        question: q,
        answer: data.answer,
        sources: data.sources || [],
      }])
      if (data.provider === 'fallback') {
        toast.warning('Groq unavailable \u2014 used fallback model', { duration: 4000 })
      }
    } catch {
      setError('Could not reach the brain API.')
      setQuestion(q)
    } finally {
      setLoading(false)
      // Focus input for next question
      setTimeout(() => inputRef.current?.focus(), 50)
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

  const handleNewQuestion = () => {
    setExchanges([])
    setQuestion('')
    setError(null)
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  const handleClose = () => {
    setExchanges([])
    setQuestion('')
    setError(null)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) handleClose() }}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-4 w-4 text-violet-400" />
              Ask Brain
            </DialogTitle>
            {exchanges.length > 0 && (
              <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs text-muted-foreground" onClick={handleNewQuestion}>
                <RotateCcw className="h-3 w-3" />
                New question
              </Button>
            )}
          </div>
        </DialogHeader>

        {/* Conversation thread */}
        {exchanges.length > 0 && (
          <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 min-h-0 pr-1">
            {exchanges.map((ex, i) => (
              <div key={i} className="space-y-2">
                {/* User question */}
                <div className="flex justify-end">
                  <div className="rounded-lg bg-primary/15 px-3 py-2 text-sm max-w-[85%]">
                    {ex.question}
                  </div>
                </div>
                {/* Answer */}
                <div className="rounded-md bg-muted/50 p-3 text-sm leading-relaxed whitespace-pre-wrap">
                  {ex.answer}
                </div>
                {/* Sources */}
                {ex.sources.length > 0 && (
                  <div className="pl-1">
                    <p className="text-[10px] text-muted-foreground mb-1 uppercase tracking-wide">Sources</p>
                    <div className="flex flex-wrap gap-1">
                      {ex.sources.map((s, j) => (
                        <button
                          key={j}
                          onClick={() => handleOpenNote(s.path)}
                          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                          title={s.snippet}
                        >
                          <FileText className="h-3 w-3 shrink-0" />
                          <span className="truncate max-w-[150px]">{s.title}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {/* Loading indicator for current question */}
            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Thinking...
              </div>
            )}
          </div>
        )}

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        {/* Input */}
        <div className="flex gap-2 pt-1">
          <Input
            ref={inputRef}
            autoFocus
            placeholder={exchanges.length > 0 ? "Ask a follow-up..." : "What do you remember about\u2026"}
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
      </DialogContent>
    </Dialog>
  )
}
