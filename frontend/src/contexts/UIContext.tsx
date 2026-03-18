import { createContext, useContext, useState } from 'react'

type View = 'notes' | 'actions' | 'people' | 'meetings' | 'projects'

interface UIContextValue {
  currentView: View
  setCurrentView: (v: View) => void
}

const UIContext = createContext<UIContextValue>(null!)
export const useUIContext = () => useContext(UIContext)

export function UIProvider({ children }: { children: React.ReactNode }) {
  const [currentView, setCurrentView] = useState<View>('notes')

  return (
    <UIContext.Provider value={{ currentView, setCurrentView }}>
      {children}
    </UIContext.Provider>
  )
}
