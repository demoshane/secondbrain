import { useRef, useState } from 'react'
import { Search, Plus, FolderUp, Sparkles, SlidersHorizontal, Brain, Settings } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useSearchContext } from '@/contexts/SearchContext'
import { useSSEContext } from '@/contexts/SSEContext'
import { useNoteContext } from '@/contexts/NoteContext'
import { cn } from '@/lib/utils'

interface Props {
  onNewNote: () => void
  onBatchCapture: () => void
  onSmartCapture: () => void
  onAskBrain: () => void
  onSettings: () => void
}

export function Topbar({ onNewNote, onBatchCapture, onSmartCapture, onAskBrain, onSettings }: Props) {
  const { query, setQuery, mode, setMode, search, clearSearch } = useSearchContext()
  const { connected } = useSSEContext()
  const { loadNotes } = useNoteContext()
  const inputRef = useRef<HTMLInputElement>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleSearch = () => {
    if (query.trim()) {
      search(query, mode)
    } else {
      clearSearch()
      loadNotes()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch()
    if (e.key === 'Escape') { clearSearch(); loadNotes() }
  }

  return (
    <div className="h-[52px] flex items-center gap-2 px-4 border-b border-border bg-background" data-testid="topbar">
      <Search className="h-4 w-4 text-muted-foreground shrink-0" />
      <Input
        ref={inputRef}
        data-testid="search-input"
        placeholder="Search notes..."
        value={query}
        onChange={e => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        className="flex-1 h-8 bg-input"
      />
      <Button
        size="sm"
        variant="ghost"
        onClick={() => setShowAdvanced(prev => !prev)}
        title="Advanced search options"
        data-testid="search-advanced-toggle"
        className="h-8 w-8 p-0"
      >
        <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
      </Button>
      {showAdvanced && (
        <Select value={mode} onValueChange={(v: string) => setMode(v as 'hybrid' | 'bm25' | 'semantic')}>
          <SelectTrigger className="w-28 h-8" data-testid="search-mode-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="hybrid">Hybrid</SelectItem>
            <SelectItem value="bm25">BM25</SelectItem>
            <SelectItem value="semantic">Semantic</SelectItem>
          </SelectContent>
        </Select>
      )}
      <Button size="sm" variant="default" data-testid="new-note-btn" onClick={onNewNote}>
        <Plus className="h-4 w-4 mr-1" />
        New Note
      </Button>
      <Button size="sm" variant="outline" data-testid="smart-capture-btn" onClick={onSmartCapture}>
        <Sparkles className="h-4 w-4 mr-1 text-orange-400" />
        Smart Capture
      </Button>
      <Button size="sm" variant="ghost" data-testid="batch-capture-btn" onClick={onBatchCapture}>
        <FolderUp className="h-4 w-4 mr-1" />
        Batch
      </Button>
      <Button size="sm" variant="outline" data-testid="ask-brain-btn" onClick={onAskBrain} className="border-violet-800/50 text-violet-300 hover:bg-violet-900/20 hover:text-violet-200">
        <Brain className="h-4 w-4 mr-1" />
        Ask Brain
      </Button>
      <Button size="sm" variant="ghost" data-testid="settings-btn" onClick={onSettings} className="h-8 w-8 p-0" title="Settings">
        <Settings className="h-4 w-4 text-muted-foreground" />
      </Button>
      <div
        data-testid="sse-status-dot"
        className={cn('h-2 w-2 rounded-full', connected ? 'bg-green-500' : 'bg-red-500')}
        title={connected ? 'Connected' : 'Disconnected'}
      />
    </div>
  )
}
