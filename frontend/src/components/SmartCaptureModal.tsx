import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Loader2, Sparkles, Check, AlertCircle, User, Trash2 } from 'lucide-react'
import { getAPI, encodePath } from '@/lib/utils'

interface SavedNote {
  title: string
  type: string
  path?: string
  error?: string
}

interface PersonStub {
  name: string
  type: string
  path?: string
}

interface PendingNote {
  title: string
  body: string
  suggested_type: string
  confidence: number
  people: string[]
}

interface Props {
  open: boolean
  onClose: () => void
}

const NOTE_TYPES = [
  'note', 'meeting', 'person', 'coding', 'project',
  'strategy', 'idea', 'personal', 'link',
]

const TYPE_COLORS: Record<string, string> = {
  meeting: 'bg-[#1a2f1a] text-[#4ade80]',
  person: 'bg-[#2a1f1f] text-[#f87171]',
  people: 'bg-[#2a1f1f] text-[#f87171]',
  project: 'bg-[#2f1f0e] text-[#fb923c]',
  idea: 'bg-[#1f2a1a] text-[#86efac]',
  link: 'bg-[#1a2a2a] text-[#2dd4bf]',
  strategy: 'bg-[#1a1f3a] text-[#818cf8]',
  coding: 'bg-[#1f2a3a] text-[#60a5fa]',
  personal: 'bg-[#2d1f2d] text-[#c084fc]',
  research: 'bg-[#2d1f5e] text-[#a78bfa]',
  note: 'bg-secondary text-[#94a3b8]',
}

export function SmartCaptureModal({ open, onClose }: Props) {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState<SavedNote[] | null>(null)
  const [pending, setPending] = useState<PendingNote[] | null>(null)
  const [personStubs, setPersonStubs] = useState<(PersonStub | string)[]>([])
  // Track user-selected types for pending items
  const [pendingTypes, setPendingTypes] = useState<Record<number, string>>({})
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)

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
      setSaved(data.notes ?? [])
      setPersonStubs(data.person_stubs || [])
      const pendingItems: PendingNote[] = data.pending_review ?? []
      setPending(pendingItems.length > 0 ? pendingItems : null)
      // Initialise type selections to the suggestions
      const initial: Record<number, string> = {}
      pendingItems.forEach((p, i) => { initial[i] = p.suggested_type })
      setPendingTypes(initial)
    } catch {
      setSaved([])
      setPending(null)
      setPersonStubs([])
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    if (!pending) return
    setSaving(true)
    try {
      const segments = pending.map((p, i) => ({
        title: p.title,
        type: pendingTypes[i] ?? p.suggested_type,
        body: p.body,
        people: p.people,
      }))
      const res = await fetch(`${getAPI()}/smart-capture/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ segments }),
      })
      const data = await res.json()
      setSaved(prev => [...(prev ?? []), ...(data.notes ?? [])])
      setPending(null)
    } catch {
      // non-fatal — user can retry
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteNote = async (index: number) => {
    const note = saved![index]
    if (!note?.path) return
    try {
      await fetch(`${getAPI()}/notes/${encodePath(note.path)}`, { method: 'DELETE' })
      setSaved(prev => prev ? prev.filter((_, i) => i !== index) : prev)
    } catch {
      // non-fatal
    } finally {
      setConfirmDelete(null)
    }
  }

  const handleClose = () => {
    setContent('')
    setSaved(null)
    setPending(null)
    setPersonStubs([])
    setPendingTypes({})
    setConfirmDelete(null)
    setLoading(false)
    setSaving(false)
    onClose()
  }

  const showResults = saved !== null
  const showReview = showResults && pending && pending.length > 0

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) handleClose() }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Smart Capture
          </DialogTitle>
        </DialogHeader>

        {/* Step 1: input */}
        {!showResults && (
          <div className="space-y-3">
            <textarea
              placeholder="Paste meeting notes, conversation dumps, or any freeform text..."
              value={content}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setContent(e.target.value)}
              rows={8}
              className="resize-y w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
        )}

        {/* Step 2: show saved + optional review */}
        {showResults && (
          <div className="space-y-4">
            {/* Auto-saved notes */}
            {(saved?.length ?? 0) > 0 && (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  {saved!.length} note{saved!.length !== 1 ? 's' : ''} saved:
                </p>
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {saved!.map((note, i) => (
                    <div key={i} className="group flex items-center gap-2 p-2 rounded border">
                      {note.error ? (
                        <span className="text-sm text-red-500">{note.error}</span>
                      ) : confirmDelete === i ? (
                        <>
                          <span className="text-sm text-muted-foreground flex-1">Delete "{note.title}"?</span>
                          <button
                            onClick={() => handleDeleteNote(i)}
                            className="text-xs text-red-500 hover:text-red-400 px-1.5 py-0.5 rounded hover:bg-red-500/10"
                          >
                            Yes
                          </button>
                          <button
                            onClick={() => setConfirmDelete(null)}
                            className="text-xs text-muted-foreground hover:text-foreground px-1.5 py-0.5 rounded hover:bg-secondary"
                          >
                            No
                          </button>
                        </>
                      ) : (
                        <>
                          <Check className="h-4 w-4 text-green-500 shrink-0" />
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${TYPE_COLORS[note.type] ?? TYPE_COLORS.note}`}>
                            {note.type}
                          </span>
                          <span className="text-sm truncate flex-1">{note.title}</span>
                          {note.path && (
                            <button
                              onClick={() => setConfirmDelete(i)}
                              className="text-muted-foreground hover:text-red-400 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                              title="Delete this note"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Person stubs created */}
            {personStubs.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-sm text-muted-foreground">
                  {personStubs.length} person stub{personStubs.length !== 1 ? 's' : ''} created
                </p>
                {personStubs.map((stub, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <User className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="px-1.5 py-0.5 rounded text-xs bg-[#2a1f1f] text-[#f87171]">person</span>
                    <span className="truncate">{typeof stub === 'string' ? stub : (stub as PersonStub).name}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Pending review */}
            {showReview && (
              <div className="space-y-2">
                <p className="text-sm text-amber-500 flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {pending.length} item{pending.length !== 1 ? 's' : ''} need{pending.length === 1 ? 's' : ''} type confirmation:
                </p>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {pending.map((item, i) => (
                    <div key={i} className="p-2 rounded border border-amber-800/40 space-y-1.5">
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-sm font-medium truncate">{item.title}</span>
                        <span className="text-xs text-muted-foreground shrink-0">
                          {Math.round(item.confidence * 100)}% sure
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">{item.body}</p>
                      <select
                        value={pendingTypes[i] ?? item.suggested_type}
                        onChange={e => setPendingTypes(prev => ({ ...prev, [i]: e.target.value }))}
                        className="w-full text-xs rounded border border-input bg-background px-2 py-1 focus:outline-none focus:ring-1 focus:ring-ring"
                      >
                        {NOTE_TYPES.map(t => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" onClick={() => setPending(null)}>
                    Skip
                  </Button>
                  <Button size="sm" onClick={handleConfirm} disabled={saving}>
                    {saving ? (
                      <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Saving...</>
                    ) : (
                      `Save ${pending.length} item${pending.length !== 1 ? 's' : ''}`
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Done button — only show when no pending review */}
            {!showReview && (
              <div className="flex justify-end">
                <Button onClick={handleClose}>Done</Button>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
