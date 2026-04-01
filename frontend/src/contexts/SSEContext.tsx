import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { getAPI } from '@/lib/utils'
import { useNoteContext } from './NoteContext'

interface SSEContextValue {
  connected: boolean
}

const SSEContext = createContext<SSEContextValue>({ connected: false })
export const useSSEContext = () => useContext(SSEContext)

export function SSEProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false)
  const { loadNotes, openNote, currentPath } = useNoteContext()
  // Use ref so SSE handler always reads the latest currentPath without re-subscribing
  const currentPathRef = useRef(currentPath)
  currentPathRef.current = currentPath

  useEffect(() => {
    const src = new EventSource(`${getAPI()}/events`)
    src.onopen = () => { setConnected(true); loadNotes() }
    const handler = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        loadNotes()
        const cp = currentPathRef.current
        if (cp && data.path === cp) openNote(cp)
      } catch {
        // malformed SSE payload — ignore
      }
    }
    src.addEventListener('note', handler)
    src.onerror = () => setConnected(false)
    return () => src.close()
  }, []) // connect once; EventSource handles native reconnect

  return (
    <SSEContext.Provider value={{ connected }}>
      {children}
    </SSEContext.Provider>
  )
}
