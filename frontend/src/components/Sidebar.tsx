import { useState } from 'react'
import { X } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { NoteTypeBadge } from '@/components/ui/note-type-badge'
import { ImportanceBadge } from '@/components/ui/importance-badge'
import { useNoteContext } from '@/contexts/NoteContext'
import { useSearchContext } from '@/contexts/SearchContext'
import { cn } from '@/lib/utils'
import type { Note } from '@/types'

const TYPE_ORDER = ['meeting', 'people', 'projects', 'idea', 'note', 'strategy', 'coding', 'personal', 'link', 'files']

function groupByType(notes: Note[]): Map<string, Note[]> {
  const typeMap = new Map<string, Note[]>()

  for (const note of notes) {
    const type = note.type || 'note'
    if (!typeMap.has(type)) typeMap.set(type, [])
    typeMap.get(type)!.push(note)
  }

  // Sort by TYPE_ORDER, remainder alphabetically
  const sorted = new Map<string, Note[]>()
  for (const t of TYPE_ORDER) {
    if (typeMap.has(t)) sorted.set(t, typeMap.get(t)!)
  }
  const remaining = Array.from(typeMap.keys())
    .filter(t => !TYPE_ORDER.includes(t))
    .sort()
  for (const t of remaining) {
    sorted.set(t, typeMap.get(t)!)
  }

  return sorted
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

interface NoteRowProps {
  note: Note
  isActive: boolean
  onClick: () => void
}

function NoteRow({ note, isActive, onClick }: NoteRowProps) {
  return (
    <button
      className={cn(
        'w-full flex items-center gap-2 px-3 py-1.5 cursor-pointer text-sm truncate group text-left',
        isActive
          ? 'bg-secondary text-foreground border-l-2 border-primary'
          : 'text-muted-foreground hover:bg-secondary/50'
      )}
      onClick={onClick}
      data-testid="note-item"
      data-path={note.path}
    >
      <NoteTypeBadge type={note.type || 'note'} className="text-[10px] shrink-0" />
      <ImportanceBadge importance={note.importance} className="text-[10px] shrink-0" />
      <span className="truncate">{((note.title || note.path.split('/').pop()) ?? '').slice(0, 30) + ((note.title || note.path.split('/').pop() || '').length > 30 ? '…' : '')}</span>
    </button>
  )
}

const IMPORTANCE_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 }

export function Sidebar() {
  const { notes, currentPath, openNote } = useNoteContext()
  const { results, tagFilter, setTagFilter, clearSearch } = useSearchContext()
  const [sortByImportance, setSortByImportance] = useState(false)

  const displayNotes = results ?? notes
  const filtered = tagFilter
    ? displayNotes.filter(n => n.tags?.includes(tagFilter))
    : displayNotes

  const sorted = sortByImportance
    ? [...filtered].sort((a, b) =>
        (IMPORTANCE_ORDER[a.importance || 'medium'] ?? 1) - (IMPORTANCE_ORDER[b.importance || 'medium'] ?? 1)
      )
    : filtered
  const grouped = groupByType(sorted)

  return (
    <div className="w-80 border-r border-border flex flex-col bg-card" data-testid="sidebar">
      {tagFilter && (
        <div className="flex items-center gap-1 px-2 py-1 bg-muted text-xs" data-testid="tag-filter-banner">
          <span className="truncate text-muted-foreground">Filtering: {tagFilter}</span>
          <Button
            variant="ghost"
            size="icon"
            className="h-4 w-4 ml-auto shrink-0"
            onClick={() => { setTagFilter(null); clearSearch() }}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}
      <div className="flex items-center px-2 py-1 border-b border-border/50">
        <button
          onClick={() => setSortByImportance(v => !v)}
          className={cn(
            "text-[10px] px-2 py-0.5 rounded",
            sortByImportance ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
          )}
          title="Sort by importance"
        >
          Importance
        </button>
      </div>
      <ScrollArea className="flex-1">
        {Array.from(grouped.entries()).map(([type, typeNotes]) => (
          <CollapsibleSection
            key={type}
            title={capitalize(type)}
            count={typeNotes.length}
            sectionId={`sidebar-type-${type}`}
            defaultOpen={true}
          >
            {typeNotes.map(note => (
              <NoteRow
                key={note.path}
                note={note}
                isActive={note.path === currentPath}
                onClick={() => openNote(note.path)}
              />
            ))}
          </CollapsibleSection>
        ))}
      </ScrollArea>
    </div>
  )
}
