import { FileText, CheckSquare, Users, Calendar, Briefcase, Brain, Gauge, Inbox, Link, Network } from 'lucide-react'
import { useUIContext } from '@/contexts/UIContext'
import { cn } from '@/lib/utils'

const TABS = [
  { id: 'notes' as const, label: 'Notes', icon: FileText },
  { id: 'actions' as const, label: 'Actions', icon: CheckSquare },
  { id: 'people' as const, label: 'People', icon: Users },
  { id: 'meetings' as const, label: 'Meetings', icon: Calendar },
  { id: 'projects' as const, label: 'Projects', icon: Briefcase },
  { id: 'intelligence' as const, label: 'Intelligence', icon: Brain },
  { id: 'performance' as const, label: 'Performance', icon: Gauge },
  { id: 'inbox' as const, label: 'Inbox', icon: Inbox },
  { id: 'links' as const, label: 'Links', icon: Link },
  { id: 'graph' as const, label: 'Graph', icon: Network },
]

export function TabBar() {
  const { currentView, setCurrentView } = useUIContext()

  return (
    <div className="h-10 flex items-center border-b border-border bg-card px-2" data-testid="tab-bar">
      {TABS.map(tab => {
        const Icon = tab.icon
        const isActive = currentView === tab.id
        return (
          <button
            key={tab.id}
            data-testid={`tab-${tab.id}`}
            onClick={() => setCurrentView(tab.id)}
            className={cn(
              'flex items-center gap-1.5 rounded-none h-full px-3 text-sm border-b-2 hover:text-foreground hover:bg-secondary/50',
              isActive
                ? 'border-primary text-foreground font-semibold'
                : 'border-transparent text-muted-foreground'
            )}
          >
            <Icon className="h-4 w-4" />
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
