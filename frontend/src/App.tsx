import { useEffect } from 'react'
import { Topbar } from './components/Topbar'
import { TabBar } from './components/TabBar'
import { Sidebar } from './components/Sidebar'
import { useNoteContext } from './contexts/NoteContext'
import { useUIContext } from './contexts/UIContext'

// Placeholder components until plan 04
function NoteViewerPlaceholder() {
  return <div className="flex-1 p-4 text-muted-foreground">Select a note</div>
}
function ActionsPagePlaceholder() {
  return <div className="flex-1 p-4 text-muted-foreground">Actions page</div>
}
function RightPanelPlaceholder() {
  return <div className="w-64 border-l p-4 text-muted-foreground text-sm">Right panel</div>
}

export default function App() {
  const { loadNotes } = useNoteContext()
  const { currentView } = useUIContext()

  useEffect(() => { loadNotes() }, [loadNotes])

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      <Topbar />
      <TabBar />
      <div className="flex flex-1 overflow-hidden">
        {currentView === 'notes' && <Sidebar />}
        <div className="flex flex-1 overflow-hidden">
          {currentView === 'notes' ? <NoteViewerPlaceholder /> : <ActionsPagePlaceholder />}
        </div>
        {currentView === 'notes' && <RightPanelPlaceholder />}
      </div>
    </div>
  )
}
