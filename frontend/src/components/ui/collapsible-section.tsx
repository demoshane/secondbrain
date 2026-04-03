import * as React from "react"
import { ChevronRight, ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"
import { InfoTip } from "@/components/ui/info-tip"

interface CollapsibleSectionProps {
  title: string
  count: number
  sectionId: string
  defaultOpen?: boolean
  children: React.ReactNode
  className?: string
  infoTip?: string
}

function CollapsibleSection({
  title,
  count,
  sectionId,
  defaultOpen = true,
  children,
  className,
  infoTip,
}: CollapsibleSectionProps) {
  const storageKey = `collapsible-section-${sectionId}`

  const [isOpen, setIsOpen] = React.useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(storageKey)
      return stored !== null ? stored === 'true' : defaultOpen
    } catch {
      return defaultOpen
    }
  })

  const toggle = () => {
    const next = !isOpen
    setIsOpen(next)
    try {
      localStorage.setItem(storageKey, String(next))
    } catch {
      // ignore storage errors
    }
  }

  return (
    <div className={cn("flex flex-col", className)} data-testid={`folder-section-${sectionId}`} data-collapsed={!isOpen}>
      <button
        type="button"
        onClick={toggle}
        className="flex items-center gap-2 px-3 py-2 w-full text-left hover:bg-secondary/50 transition-colors"
        data-testid={`folder-header-${sectionId}`}
      >
        {isOpen ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
        <span className="flex-1 text-sm font-medium text-foreground flex items-center">
          {title}
          {infoTip && <InfoTip text={infoTip} />}
        </span>
        <span className="inline-flex items-center justify-center rounded-full bg-secondary text-muted-foreground px-2 text-xs min-w-[1.25rem]">
          {count}
        </span>
      </button>
      <div
        className={cn(
          "overflow-hidden transition-all duration-200",
          isOpen ? "max-h-[9999px] opacity-100" : "max-h-0 opacity-0"
        )}
      >
        {children}
      </div>
    </div>
  )
}

export { CollapsibleSection }
