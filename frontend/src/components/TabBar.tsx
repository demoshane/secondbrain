import { Button } from '@/components/ui/button'
import { useUIContext } from '@/contexts/UIContext'
import { cn } from '@/lib/utils'

const TABS = [
  { id: 'notes' as const, label: 'Notes' },
  { id: 'actions' as const, label: 'Action Items' },
  { id: 'people' as const, label: 'People' },
  { id: 'meetings' as const, label: 'Meetings' },
  { id: 'projects' as const, label: 'Projects' },
]

export function TabBar() {
  const { currentView, setCurrentView } = useUIContext()

  return (
    <div className="flex border-b bg-background px-2" data-testid="tab-bar">
      {TABS.map(tab => (
        <Button
          key={tab.id}
          variant="ghost"
          size="sm"
          data-testid={`tab-${tab.id}`}
          onClick={() => setCurrentView(tab.id)}
          className={cn(
            'rounded-none border-b-2 h-9',
            currentView === tab.id
              ? 'border-primary text-primary font-medium'
              : 'border-transparent text-muted-foreground'
          )}
        >
          {tab.label}
        </Button>
      ))}
    </div>
  )
}
