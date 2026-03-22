import { Command } from 'cmdk'
import { useNoteContext } from '@/contexts/NoteContext'
import { useUIContext } from '@/contexts/UIContext'
import { cn } from '@/lib/utils'

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
  onOpenSmartCapture: () => void
  onOpenNewNote: () => void
}

const PAGE_VIEWS = [
  { label: 'Notes', value: 'notes' },
  { label: 'Actions', value: 'actions' },
  { label: 'Persons', value: 'people' },
  { label: 'Meetings', value: 'meetings' },
  { label: 'Projects', value: 'projects' },
  { label: 'Links', value: 'links' },
  { label: 'Intelligence', value: 'intelligence' },
  { label: 'Inbox', value: 'inbox' },
] as const

export function CommandPalette({ open, onClose, onOpenSmartCapture, onOpenNewNote }: CommandPaletteProps) {
  const { notes, openNote } = useNoteContext()
  const { setCurrentView } = useUIContext()

  return (
    <div
      className={cn('fixed inset-0 z-50 bg-black/50', !open && 'hidden')}
      onClick={onClose}
    >
      <div
        className="fixed left-1/2 top-1/3 -translate-x-1/2 w-full max-w-lg"
        onClick={e => e.stopPropagation()}
      >
        <Command className="border shadow-md rounded-lg bg-popover overflow-hidden">
          <Command.Input
            placeholder="Type a command or search..."
            className="w-full px-4 py-3 text-sm outline-none bg-transparent border-b border-border placeholder:text-muted-foreground"
          />
          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              No matching notes or commands.
            </Command.Empty>

            <Command.Group heading="Navigation" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground">
              {PAGE_VIEWS.map(page => (
                <Command.Item
                  key={page.value}
                  value={`go to ${page.label}`}
                  onSelect={() => {
                    setCurrentView(page.value)
                    onClose()
                  }}
                  className="flex items-center gap-2 px-2 py-1.5 text-sm rounded cursor-pointer aria-selected:bg-accent aria-selected:text-accent-foreground"
                >
                  Go to {page.label}
                </Command.Item>
              ))}
              {notes.map(note => (
                <Command.Item
                  key={note.path}
                  value={note.title}
                  onSelect={() => {
                    setCurrentView('notes')
                    openNote(note.path)
                    onClose()
                  }}
                  className="flex items-center gap-2 px-2 py-1.5 text-sm rounded cursor-pointer aria-selected:bg-accent aria-selected:text-accent-foreground"
                >
                  {note.title}
                </Command.Item>
              ))}
            </Command.Group>

            <Command.Group heading="Capture" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground">
              <Command.Item
                value="quick capture"
                onSelect={() => { onOpenNewNote(); onClose() }}
                className="flex items-center gap-2 px-2 py-1.5 text-sm rounded cursor-pointer aria-selected:bg-accent aria-selected:text-accent-foreground"
              >
                Quick Capture
              </Command.Item>
              <Command.Item
                value="smart capture"
                onSelect={() => { onOpenSmartCapture(); onClose() }}
                className="flex items-center gap-2 px-2 py-1.5 text-sm rounded cursor-pointer aria-selected:bg-accent aria-selected:text-accent-foreground"
              >
                Smart Capture
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  )
}
