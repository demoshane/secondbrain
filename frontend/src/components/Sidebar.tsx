import { X } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { CollapsibleSection } from '@/components/ui/collapsible-section'
import { NoteTypeBadge } from '@/components/ui/note-type-badge'
import { useNoteContext } from '@/contexts/NoteContext'
import { useSearchContext } from '@/contexts/SearchContext'
import { cn } from '@/lib/utils'
import type { Note } from '@/types'

const TYPE_ORDER = ['meeting', 'people', 'projects', 'idea', 'note', 'strategy', 'coding', 'personal', 'link', 'files']

function groupByType(notes: Note[]): Map<string, Note[]> {
  const grouped = new Map<string, Note[]>()
  for (const note of notes) {
    const type = note.type || 'note'
    if (!grouped.has(type)) grouped.set(type, [])
    grouped.get(type)!.push(note)
  }
  // Sort by TYPE_ORDER
  const sorted = new Map<string, Note[]>()
  for (const t of TYPE_ORDER) {
    if (grouped.has(t)) sorted.set(t, grouped.get(t)!)
  }
  // Append any types not in TYPE_ORDER
  for (const [t, typeNotes] of grouped) {
    if (!sorted.has(t)) sorted.set(t, typeNotes)
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
      data-testid={`note-row-${encodeURIComponent(note.path)}`}
    >
      <NoteTypeBadge type={note.type || 'note'} className="text-[10px] shrink-0" />
      <span className="truncate">{note.title || note.path.split('/').pop()}</span>
    </button>
  )
}

export function Sidebar() {
  const { notes, currentPath, openNote } = useNoteContext()
  const { results, tagFilter, setTagFilter, clearSearch } = useSearchContext()

  const displayNotes = results ?? notes
  const filtered = tagFilter
    ? displayNotes.filter(n => n.tags?.includes(tagFilter))
    : displayNotes

  const grouped = groupByType(filtered)

  return (
    <div className="w-64 border-r border-border flex flex-col bg-card" data-testid="sidebar">
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
      <ScrollArea className="flex-1">
        {Array.from(grouped.entries()).map(([type, typeNotes]) => (
          <CollapsibleSection
            key={type}
            title={capitalize(type)}
            count={typeNotes.length}
            sectionId={`sidebar-${type}`}
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
