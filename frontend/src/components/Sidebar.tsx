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

const FOLDER_ORDER = ['meetings', 'people', 'person', 'projects', 'ideas', 'notes', 'strategy', 'coding', 'personal', 'links', 'files']

function groupByFolderThenType(notes: Note[]): Map<string, Map<string, Note[]>> {
  const folderMap = new Map<string, Map<string, Note[]>>()

  for (const note of notes) {
    const slashIdx = note.path.indexOf('/')
    const folder = slashIdx !== -1 ? note.path.slice(0, slashIdx) : 'other'
    const type = note.type || 'note'

    if (!folderMap.has(folder)) folderMap.set(folder, new Map<string, Note[]>())
    const typeMap = folderMap.get(folder)!
    if (!typeMap.has(type)) typeMap.set(type, [])
    typeMap.get(type)!.push(note)
  }

  // Sort folders by FOLDER_ORDER, remainder alphabetically
  const sortedFolders = new Map<string, Map<string, Note[]>>()
  for (const f of FOLDER_ORDER) {
    if (folderMap.has(f)) sortedFolders.set(f, folderMap.get(f)!)
  }
  const remaining = Array.from(folderMap.keys())
    .filter(f => !FOLDER_ORDER.includes(f))
    .sort()
  for (const f of remaining) {
    sortedFolders.set(f, folderMap.get(f)!)
  }

  // Sort types within each folder by TYPE_ORDER
  for (const [folder, typeMap] of sortedFolders) {
    const sortedTypes = new Map<string, Note[]>()
    for (const t of TYPE_ORDER) {
      if (typeMap.has(t)) sortedTypes.set(t, typeMap.get(t)!)
    }
    for (const [t, typeNotes] of typeMap) {
      if (!sortedTypes.has(t)) sortedTypes.set(t, typeNotes)
    }
    sortedFolders.set(folder, sortedTypes)
  }

  return sortedFolders
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

  const grouped = groupByFolderThenType(filtered)

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
        {Array.from(grouped.entries()).map(([folder, typeMap]) => (
          <CollapsibleSection
            key={folder}
            title={capitalize(folder)}
            count={Array.from(typeMap.values()).reduce((sum, notes) => sum + notes.length, 0)}
            sectionId={`sidebar-folder-${folder}`}
            defaultOpen={true}
          >
            {Array.from(typeMap.entries()).map(([type, typeNotes]) => (
              <div key={type} className="pl-2">
                <CollapsibleSection
                  title={capitalize(type)}
                  count={typeNotes.length}
                  sectionId={`sidebar-${folder}-${type}`}
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
              </div>
            ))}
          </CollapsibleSection>
        ))}
      </ScrollArea>
    </div>
  )
}
