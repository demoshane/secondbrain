import { ChevronDown, ChevronRight, X } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { useNoteContext } from '@/contexts/NoteContext'
import { useSearchContext } from '@/contexts/SearchContext'
import { useCollapseState } from '@/hooks/useCollapseState'
import { cn } from '@/lib/utils'
import type { Note } from '@/types'

function groupNotes(notes: Note[]): Map<string, Map<string, Note[]>> {
  const grouped = new Map<string, Map<string, Note[]>>()
  for (const note of notes) {
    const folder = note.folder || 'other'
    const type = note.type || 'note'
    if (!grouped.has(folder)) grouped.set(folder, new Map())
    const byType = grouped.get(folder)!
    if (!byType.has(type)) byType.set(type, [])
    byType.get(type)!.push(note)
  }
  return grouped
}

export function Sidebar() {
  const { notes, currentPath, openNote } = useNoteContext()
  const { results, tagFilter, setTagFilter, clearSearch } = useSearchContext()
  const { prefs, toggle } = useCollapseState()

  const displayNotes = results ?? notes
  const filtered = tagFilter
    ? displayNotes.filter(n => n.tags?.includes(tagFilter))
    : displayNotes

  const grouped = groupNotes(filtered)

  return (
    <div className="w-56 border-r flex flex-col" data-testid="sidebar">
      {tagFilter && (
        <div className="flex items-center gap-1 px-2 py-1 bg-muted text-xs" data-testid="tag-filter-banner">
          <span>Filtering: {tagFilter}</span>
          <Button
            variant="ghost"
            size="icon"
            className="h-4 w-4 ml-auto"
            onClick={() => { setTagFilter(null); clearSearch() }}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}
      <ScrollArea className="flex-1">
        {Array.from(grouped.entries()).map(([folder, byType]) => (
          <div key={folder} data-testid={`folder-section-${folder}`} data-collapsed={!!prefs[`folder:${folder}`]}>
            <button
              className="w-full flex items-center gap-1 px-2 py-1 text-xs font-semibold uppercase text-muted-foreground hover:bg-muted"
              onClick={() => toggle(`folder:${folder}`)}
              data-testid={`folder-header-${folder}`}
            >
              {prefs[`folder:${folder}`]
                ? <ChevronRight className="h-3 w-3" />
                : <ChevronDown className="h-3 w-3" />
              }
              {folder}
            </button>
            {!prefs[`folder:${folder}`] && Array.from(byType.entries()).map(([type, typeNotes]) => (
              <div key={type}>
                <button
                  className="w-full flex items-center gap-1 pl-4 pr-2 py-0.5 text-xs text-muted-foreground hover:bg-muted"
                  onClick={() => toggle(`type:${folder}:${type}`)}
                  data-testid={`collapse-type-${type}`}
                >
                  {prefs[`type:${folder}:${type}`]
                    ? <ChevronRight className="h-3 w-3" />
                    : <ChevronDown className="h-3 w-3" />
                  }
                  {type}
                </button>
                {!prefs[`type:${folder}:${type}`] && typeNotes.map(note => (
                  <button
                    key={note.path}
                    data-testid="note-item"
                    data-path={note.path}
                    onClick={() => openNote(note.path)}
                    className={cn(
                      'w-full text-left pl-7 pr-2 py-0.5 text-sm truncate hover:bg-muted',
                      currentPath === note.path && 'bg-accent text-accent-foreground font-medium'
                    )}
                  >
                    {note.title || note.path.split('/').pop()}
                  </button>
                ))}
              </div>
            ))}
          </div>
        ))}
      </ScrollArea>
    </div>
  )
}
