import { useEffect, useState } from 'react'
import { Topbar } from './components/Topbar'
import { TabBar } from './components/TabBar'
import { Sidebar } from './components/Sidebar'
import { NoteViewer } from './components/NoteViewer'
import { RightPanel } from './components/RightPanel'
import { ActionsPage } from './components/ActionsPage'
import { PeoplePage } from './components/PeoplePage'
import { MeetingsPage } from './components/MeetingsPage'
import { ProjectsPage } from './components/ProjectsPage'
import { IntelligencePage } from './components/IntelligencePage'
import { InboxPage } from './components/InboxPage'
import { LinksPage } from './components/LinksPage'
import { NewNoteModal } from './components/NewNoteModal'
import { DeleteNoteModal } from './components/DeleteNoteModal'
import { FileUploadModal } from './components/FileUploadModal'
import { BatchCaptureModal } from './components/BatchCaptureModal'
import { SmartCaptureModal } from './components/SmartCaptureModal'
import { CommandPalette } from './components/CommandPalette'
import { useNoteContext } from './contexts/NoteContext'
import { useUIContext } from './contexts/UIContext'
import { Button } from './components/ui/button'
import { Trash2, Upload } from 'lucide-react'
import { Toaster } from 'sonner'

export default function App() {
  const { loadNotes, currentNote, currentPath } = useNoteContext()
  const { currentView } = useUIContext()
  const [showNewNote, setShowNewNote] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [showBatch, setShowBatch] = useState(false)
  const [showSmartCapture, setShowSmartCapture] = useState(false)
  const [showPalette, setShowPalette] = useState(false)

  useEffect(() => { loadNotes() }, [loadNotes])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowPalette(prev => !prev)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      <Topbar
        onNewNote={() => setShowNewNote(true)}
        onBatchCapture={() => setShowBatch(true)}
        onSmartCapture={() => setShowSmartCapture(true)}
      />
      <TabBar />
      <div className="flex flex-1 overflow-hidden">
        {currentView === 'notes' && <Sidebar />}
        <div className="flex flex-1 flex-col overflow-hidden">
          {currentView === 'notes' ? (
            currentNote ? (
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="flex items-center gap-1 px-2 py-1 border-b">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowUpload(true)}
                    disabled={!currentPath}
                    data-testid="upload-btn"
                  >
                    <Upload className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowDelete(true)}
                    disabled={!currentPath}
                    data-testid="delete-btn"
                    className="text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <NoteViewer note={currentNote} />
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-muted-foreground" data-testid="no-note-selected">
                Select a note
              </div>
            )
          ) : currentView === 'actions' ? (
            <ActionsPage />
          ) : currentView === 'people' ? (
            <PeoplePage />
          ) : currentView === 'meetings' ? (
            <MeetingsPage />
          ) : currentView === 'projects' ? (
            <ProjectsPage />
          ) : currentView === 'intelligence' ? (
            <IntelligencePage />
          ) : currentView === 'inbox' ? (
            <InboxPage />
          ) : currentView === 'links' ? (
            <LinksPage />
          ) : null}
        </div>
        {currentView === 'notes' && <RightPanel />}
      </div>

      <NewNoteModal open={showNewNote} onClose={() => setShowNewNote(false)} />
      <DeleteNoteModal
        open={showDelete}
        notePath={currentPath ?? ''}
        noteTitle={currentNote?.title ?? ''}
        onClose={() => setShowDelete(false)}
      />
      <FileUploadModal open={showUpload} onClose={() => setShowUpload(false)} />
      <BatchCaptureModal open={showBatch} onClose={() => setShowBatch(false)} />
      <SmartCaptureModal open={showSmartCapture} onClose={() => setShowSmartCapture(false)} />
      <CommandPalette
        open={showPalette}
        onClose={() => setShowPalette(false)}
        onOpenSmartCapture={() => setShowSmartCapture(true)}
        onOpenNewNote={() => setShowNewNote(true)}
      />
      <Toaster position="bottom-right" duration={3000} />
    </div>
  )
}
