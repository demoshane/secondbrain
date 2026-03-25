import { useState, useEffect, useRef } from 'react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { getAPI } from '@/lib/utils'

interface Person {
  path: string
  title: string
}

interface PersonAutocompleteProps {
  onAdd: (personPath: string) => void
  existingPeople: string[]
  onBlur?: () => void
}

export function PersonAutocomplete({ onAdd, existingPeople, onBlur }: PersonAutocompleteProps) {
  const [value, setValue] = useState('')
  const [people, setPeople] = useState<Person[]>([])
  const [filtered, setFiltered] = useState<Person[]>([])
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const [showDropdown, setShowDropdown] = useState(false)
  const fetchedRef = useRef(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const ensureFetched = () => {
    if (fetchedRef.current) return
    fetchedRef.current = true
    fetch(getAPI() + '/persons')
      .then(r => r.json())
      .then(d => setPeople((d.people ?? []).map((p: Person) => ({ path: p.path, title: p.title }))))
      .catch(() => {})
  }

  useEffect(() => {
    if (!value) {
      setFiltered([])
      setShowDropdown(false)
      return
    }
    const lower = value.toLowerCase()
    const matches = people.filter(
      p => p.title.toLowerCase().includes(lower) && !existingPeople.includes(p.path)
    )
    setFiltered(matches)
    setShowDropdown(matches.length > 0)
    setHighlightIndex(-1)
  }, [value, people, existingPeople])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
        onBlur?.()
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onBlur])

  const select = (person: Person) => {
    onAdd(person.path)
    setValue('')
    setShowDropdown(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' && showDropdown) {
      e.preventDefault()
      setHighlightIndex(i => (i + 1) % filtered.length)
    } else if (e.key === 'ArrowUp' && showDropdown) {
      e.preventDefault()
      setHighlightIndex(i => (i - 1 + filtered.length) % filtered.length)
    } else if (e.key === 'Enter' && showDropdown && highlightIndex >= 0) {
      e.preventDefault()
      select(filtered[highlightIndex])
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
      onBlur?.()
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <Input
        value={value}
        aria-label="Add person"
        onChange={e => { ensureFetched(); setValue(e.target.value) }}
        onFocus={ensureFetched}
        onKeyDown={handleKeyDown}
        placeholder="Add person..."
        className="text-xs h-7 w-28"
        autoFocus
      />
      {showDropdown && (
        <ul className="absolute z-50 mt-1 w-48 bg-popover border border-border rounded-md shadow-md max-h-[160px] overflow-auto">
          {filtered.map((person, index) => (
            <li
              key={person.path}
              className={cn(
                "px-3 py-1.5 text-sm cursor-pointer",
                index === highlightIndex && "bg-accent text-accent-foreground"
              )}
              onMouseDown={() => select(person)}
            >
              {person.title}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
