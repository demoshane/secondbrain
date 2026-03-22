import { useState, useEffect, useRef } from 'react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { getAPI } from '@/lib/utils'

interface TagAutocompleteProps {
  value: string
  onChange: (value: string) => void
  onSelect: (tag: string) => void
  onBlur?: () => void
  placeholder?: string
}

export function TagAutocomplete({ value, onChange, onSelect, onBlur, placeholder }: TagAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [filtered, setFiltered] = useState<string[]>([])
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const [showDropdown, setShowDropdown] = useState(false)
  const fetchedRef = useRef(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Fetch all tags once on first keystroke
  const ensureFetched = () => {
    if (fetchedRef.current) return
    fetchedRef.current = true
    fetch(getAPI() + '/tags')
      .then(r => r.json())
      .then(d => setSuggestions(d.tags ?? []))
      .catch(() => {})
  }

  // Filter client-side on each value change
  useEffect(() => {
    if (!value) {
      setFiltered([])
      setShowDropdown(false)
      return
    }
    const lower = value.toLowerCase()
    const matches = suggestions.filter(s => s.toLowerCase().startsWith(lower))
    setFiltered(matches)
    setShowDropdown(matches.length > 0)
    setHighlightIndex(-1)
  }, [value, suggestions])

  // Click-outside handler
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' && showDropdown) {
      e.preventDefault()
      setHighlightIndex(i => (i + 1) % filtered.length)
    } else if (e.key === 'ArrowUp' && showDropdown) {
      e.preventDefault()
      setHighlightIndex(i => (i - 1 + filtered.length) % filtered.length)
    } else if (e.key === 'Enter') {
      if (showDropdown && highlightIndex >= 0 && highlightIndex < filtered.length) {
        e.preventDefault()
        onSelect(filtered[highlightIndex])
        setShowDropdown(false)
      } else if (value.trim()) {
        // No dropdown selection — call onSelect with the typed value directly
        e.preventDefault()
        onSelect(value.trim())
        setShowDropdown(false)
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
      if (onBlur) onBlur()
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <Input
        value={value}
        onChange={e => {
          ensureFetched()
          onChange(e.target.value)
        }}
        onFocus={ensureFetched}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="text-xs h-7 w-24"
        autoFocus
      />
      {showDropdown && (
        <ul className="absolute z-50 mt-1 w-full bg-popover border border-border rounded-md shadow-md max-h-[160px] overflow-auto">
          {filtered.map((tag, index) => (
            <li
              key={tag}
              className={cn(
                "px-3 py-1.5 text-sm cursor-pointer",
                index === highlightIndex && "bg-accent text-accent-foreground"
              )}
              onMouseDown={() => {
                onSelect(tag)
                setShowDropdown(false)
              }}
            >
              {tag}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
