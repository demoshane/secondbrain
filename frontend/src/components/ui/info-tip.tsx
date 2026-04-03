import { HelpCircle } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

interface InfoTipProps {
  text: string
}

export function InfoTip({ text }: InfoTipProps) {
  const [open, setOpen] = useState(false)
  const [above, setAbove] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open || !triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    // Show above if too close to bottom of viewport
    setAbove(rect.bottom + 120 > window.innerHeight)
  }, [open])

  return (
    <span className="relative inline-flex items-center ml-1">
      <button
        ref={triggerRef}
        type="button"
        className="text-muted-foreground hover:text-foreground transition-colors"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        aria-label="More info"
      >
        <HelpCircle className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div
          className={`absolute z-50 w-56 rounded-md border border-border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md left-1/2 -translate-x-1/2 normal-case font-normal ${
            above ? 'bottom-full mb-1.5' : 'top-full mt-1.5'
          }`}
        >
          {text}
        </div>
      )}
    </span>
  )
}
