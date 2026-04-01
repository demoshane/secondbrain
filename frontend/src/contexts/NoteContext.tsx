import { createContext, useContext, useState, useCallback } from 'react'
import { getAPI, encodePath } from '@/lib/utils'
import { useUIContext } from '@/contexts/UIContext'
import type { Note } from '@/types'

interface NoteContextValue {
  notes: Note[]
  currentPath: string | null
  currentNote: Note | null
  loadNotes: () => Promise<void>
  openNote: (path: string) => Promise<void>
  openNoteQuiet: (path: string) => Promise<void>
  isDirty: boolean
  setIsDirty: (v: boolean) => void
}

const NoteContext = createContext<NoteContextValue>(null!)
export const useNoteContext = () => useContext(NoteContext)

export function NoteProvider({ children }: { children: React.ReactNode }) {
  const [notes, setNotes] = useState<Note[]>([])
  const [currentPath, setCurrentPath] = useState<string | null>(null)
  const [currentNote, setCurrentNote] = useState<Note | null>(null)
  const [isDirty, setIsDirty] = useState(false)
  const { pushNoteNav } = useUIContext()

  const loadNotes = useCallback(async () => {
    const res = await fetch(`${getAPI()}/notes`)
    const data = await res.json()
    setNotes(data.notes ?? [])
  }, [])

  /** Open a note and push current position onto navigation history */
  const openNote = useCallback(async (path: string) => {
    pushNoteNav(path)
    const encoded = encodePath(path)
    const res = await fetch(`${getAPI()}/notes/${encoded}`)
    if (!res.ok) return
    const note = await res.json()
    setCurrentPath(path)
    setCurrentNote(note)
    setIsDirty(false)
  }, [pushNoteNav])

  /** Open a note without pushing history (used by goBack restoration) */
  const openNoteQuiet = useCallback(async (path: string) => {
    const encoded = encodePath(path)
    const res = await fetch(`${getAPI()}/notes/${encoded}`)
    if (!res.ok) return
    const note = await res.json()
    setCurrentPath(path)
    setCurrentNote(note)
    setIsDirty(false)
  }, [])

  return (
    <NoteContext.Provider value={{ notes, currentPath, currentNote, loadNotes, openNote, openNoteQuiet, isDirty, setIsDirty }}>
      {children}
    </NoteContext.Provider>
  )
}
