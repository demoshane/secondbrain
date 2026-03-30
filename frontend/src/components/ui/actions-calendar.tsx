import { useState, useMemo } from 'react'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ActionItem } from '@/types'

interface ActionsCalendarProps {
  actions: ActionItem[]
  onToggle: (id: number) => void
  onAddAction: (date: string) => void
  onOpen?: (item: ActionItem) => void
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function getMonthGrid(year: number, month: number): (Date | null)[][] {
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  // Monday-first: convert Sun=0 → Mon=0
  const startDow = (firstDay.getDay() + 6) % 7
  const daysInMonth = lastDay.getDate()

  const cells: (Date | null)[] = []
  for (let i = 0; i < startDow; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d))
  while (cells.length % 7 !== 0) cells.push(null)

  const rows: (Date | null)[][] = []
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7))
  return rows
}

function toDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function ActionsCalendar({ actions, onToggle, onAddAction, onOpen }: ActionsCalendarProps) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())

  const prevMonth = () => {
    if (month === 0) { setYear(y => y - 1); setMonth(11) }
    else setMonth(m => m - 1)
  }
  const nextMonth = () => {
    if (month === 11) { setYear(y => y + 1); setMonth(0) }
    else setMonth(m => m + 1)
  }
  const goToday = () => {
    setYear(today.getFullYear())
    setMonth(today.getMonth())
  }

  const grid = useMemo(() => getMonthGrid(year, month), [year, month])

  const actionsByDate = useMemo(() => {
    const map = new Map<string, ActionItem[]>()
    for (const a of actions) {
      if (a.due_date) {
        const key = a.due_date.slice(0, 10)
        if (!map.has(key)) map.set(key, [])
        map.get(key)!.push(a)
      }
    }
    return map
  }, [actions])

  const monthLabel = new Date(year, month).toLocaleString('default', {
    month: 'long',
    year: 'numeric',
  })
  const todayStr = toDateStr(today)

  return (
    <div className="flex flex-col h-full select-none">
      {/* Month navigation */}
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={prevMonth}
          className="p-1.5 rounded hover:bg-secondary/50 transition-colors"
          aria-label="Previous month"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-semibold flex-1 text-center">{monthLabel}</span>
        <button
          onClick={nextMonth}
          className="p-1.5 rounded hover:bg-secondary/50 transition-colors"
          aria-label="Next month"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <button
          onClick={goToday}
          className="text-xs px-2 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
        >
          Today
        </button>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-1 border-b border-border pb-1">
        {WEEKDAYS.map(d => (
          <div key={d} className="text-center text-xs font-medium text-muted-foreground py-1">
            {d}
          </div>
        ))}
      </div>

      {/* Day grid */}
      <div className="flex-1 grid gap-px" style={{ gridTemplateRows: `repeat(${grid.length}, 1fr)` }}>
        {grid.map((row, ri) => (
          <div key={ri} className="grid grid-cols-7 gap-px">
            {row.map((date, ci) => {
              if (!date) {
                return (
                  <div
                    key={ci}
                    className="rounded bg-secondary/5 min-h-[90px]"
                  />
                )
              }

              const dateStr = toDateStr(date)
              const dayActions = actionsByDate.get(dateStr) ?? []
              const isToday = dateStr === todayStr
              const isPast = date < today

              const MAX_VISIBLE = 3
              const visible = dayActions.slice(0, MAX_VISIBLE)
              const overflow = dayActions.length - MAX_VISIBLE

              return (
                <div
                  key={ci}
                  role="button"
                  tabIndex={0}
                  aria-label={`${dateStr}${dayActions.length ? `, ${dayActions.length} action${dayActions.length > 1 ? 's' : ''}` : ''}`}
                  onClick={() => onAddAction(dateStr)}
                  onKeyDown={e => e.key === 'Enter' && onAddAction(dateStr)}
                  className={cn(
                    "group relative rounded p-1.5 min-h-[90px] cursor-pointer transition-colors border",
                    isToday
                      ? "bg-primary/10 border-primary/40"
                      : "bg-secondary/10 border-transparent hover:bg-secondary/30 hover:border-border",
                    isPast && !isToday && "opacity-60"
                  )}
                >
                  {/* Day number */}
                  <div className={cn(
                    "text-xs font-medium mb-1 w-5 h-5 flex items-center justify-center rounded-full",
                    isToday
                      ? "bg-primary text-primary-foreground"
                      : "text-foreground"
                  )}>
                    {date.getDate()}
                  </div>

                  {/* Action chips */}
                  <div className="flex flex-col gap-0.5">
                    {visible.map(a => (
                      <div
                        key={a.id}
                        className={cn(
                          "flex items-center gap-1 text-xs px-1 py-0.5 rounded w-full leading-tight",
                          a.done
                            ? "text-muted-foreground bg-secondary/40"
                            : "text-foreground bg-primary/20"
                        )}
                      >
                        <button
                          type="button"
                          onClick={e => { e.stopPropagation(); onToggle(a.id) }}
                          aria-label={a.done ? 'Mark open' : 'Mark done'}
                          className="shrink-0 w-3 h-3 rounded-sm border border-current flex items-center justify-center hover:bg-current/20 transition-colors"
                        >
                          {a.done && <span className="text-[8px] leading-none">✓</span>}
                        </button>
                        <button
                          type="button"
                          onClick={e => { e.stopPropagation(); onOpen?.(a) }}
                          title={a.text}
                          className={cn(
                            "flex-1 text-left truncate hover:underline",
                            a.done && "line-through"
                          )}
                        >
                          {a.text}
                        </button>
                      </div>
                    ))}
                    {overflow > 0 && (
                      <span className="text-xs text-muted-foreground px-1">
                        +{overflow} more
                      </span>
                    )}
                  </div>

                  {/* Add hint on hover */}
                  <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-60 transition-opacity pointer-events-none">
                    <Plus className="h-3 w-3 text-muted-foreground" />
                  </div>
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
