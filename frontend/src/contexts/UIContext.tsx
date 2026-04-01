import { createContext, useContext, useState, useCallback, useRef } from 'react'

type View = 'notes' | 'actions' | 'people' | 'meetings' | 'projects' | 'intelligence' | 'performance' | 'inbox' | 'links'

interface NavEntry {
  view: View
  notePath?: string | null
}

const MAX_HISTORY = 10

interface UIContextValue {
  currentView: View
  setCurrentView: (v: View) => void
  /** Push a note-level navigation onto the history stack */
  pushNoteNav: (notePath: string) => void
  goBack: () => NavEntry | null
  canGoBack: boolean
}

const UIContext = createContext<UIContextValue>(null!)
export const useUIContext = () => useContext(UIContext)

export function UIProvider({ children }: { children: React.ReactNode }) {
  const [currentView, setCurrentViewRaw] = useState<View>('notes')
  const [canGoBack, setCanGoBack] = useState(false)

  // History stack stored in ref to avoid re-renders on every push
  const historyRef = useRef<NavEntry[]>([])
  // Track current note path for building history entries
  const currentNoteRef = useRef<string | null>(null)
  // Guard against re-entrant pushes during goBack
  const restoringRef = useRef(false)

  const pushHistory = useCallback((entry: NavEntry) => {
    const stack = historyRef.current
    // Don't push duplicates of current position
    const last = stack[stack.length - 1]
    if (last && last.view === entry.view && last.notePath === entry.notePath) return
    stack.push(entry)
    if (stack.length > MAX_HISTORY) stack.shift()
    setCanGoBack(stack.length > 0)
  }, [])

  const setCurrentView = useCallback((v: View) => {
    if (restoringRef.current) {
      // During goBack, just update state without pushing history
      setCurrentViewRaw(v)
      return
    }
    // Save current position before navigating
    pushHistory({ view: currentViewRef.current, notePath: currentNoteRef.current })
    setCurrentViewRaw(v)
    currentViewRef.current = v
    // Clear note context when switching away from notes
    if (v !== 'notes') currentNoteRef.current = null
  }, [pushHistory])

  // Ref to track current view synchronously (useState is async)
  const currentViewRef = useRef<View>('notes')
  // Keep ref in sync — needed because setCurrentView closes over initial value
  currentViewRef.current = currentView

  const pushNoteNav = useCallback((notePath: string) => {
    if (restoringRef.current) return
    pushHistory({ view: currentViewRef.current, notePath: currentNoteRef.current })
    currentNoteRef.current = notePath
  }, [pushHistory])

  const goBack = useCallback((): NavEntry | null => {
    const stack = historyRef.current
    if (stack.length === 0) return null
    const entry = stack.pop()!
    setCanGoBack(stack.length > 0)
    restoringRef.current = true
    setCurrentViewRaw(entry.view)
    currentViewRef.current = entry.view
    currentNoteRef.current = entry.notePath ?? null
    restoringRef.current = false
    return entry
  }, [])

  return (
    <UIContext.Provider value={{ currentView, setCurrentView, pushNoteNav, goBack, canGoBack }}>
      {children}
    </UIContext.Provider>
  )
}
