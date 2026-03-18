import { useRef } from 'react'
import { Search, Plus, FolderSync } from 'lucide-react'
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
}

export function Topbar({ onNewNote, onBatchCapture }: Props) {
  const { query, setQuery, mode, setMode, search, clearSearch } = useSearchContext()
  const { connected } = useSSEContext()
  const { loadNotes } = useNoteContext()
  const inputRef = useRef<HTMLInputElement>(null)

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
    <div className="flex items-center gap-2 px-3 py-2 border-b bg-background" data-testid="topbar">
      <div className="flex-1 flex items-center gap-2">
        <Search className="h-4 w-4 text-muted-foreground shrink-0" />
        <Input
          ref={inputRef}
          data-testid="search-input"
          placeholder="Search notes…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          className="h-8"
        />
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
      </div>
      <Button size="sm" variant="outline" data-testid="new-note-btn" onClick={onNewNote}>
        <Plus className="h-4 w-4 mr-1" />
        New Note
      </Button>
      <Button size="sm" variant="ghost" data-testid="batch-capture-btn" onClick={onBatchCapture} title="Batch Capture">
        <FolderSync className="h-4 w-4" />
      </Button>
      <div
        data-testid="sse-status-dot"
        className={cn('h-2 w-2 rounded-full', connected ? 'bg-green-500' : 'bg-red-400')}
        title={connected ? 'Live' : 'Disconnected'}
      />
    </div>
  )
}
