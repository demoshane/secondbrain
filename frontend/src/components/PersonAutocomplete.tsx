import { useState, useEffect, useRef } from 'react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { getAPI } from '@/lib/utils'

interface Person {
  path: string
  title: string
}

interface PersonAutocompleteProps {
  onAdd: (name: string) => void
  existingPeople: string[]
  onBlur?: () => void
}

export function PersonAutocomplete({ onAdd, existingPeople, onBlur }: PersonAutocompleteProps) {
  const [value, setValue] = useState('')
  const [people, setPeople] = useState<Person[]>([])
  const [filtered, setFiltered] = useState<Person[]>([])
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const [showDropdown, setShowDropdown] = useState(false)
  const [creating, setCreating] = useState(false)
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

  const trimmed = value.trim()
  const showCreate = Boolean(
    trimmed && !filtered.some(p => p.title.toLowerCase() === trimmed.toLowerCase())
  )
  const totalItems = filtered.length + (showCreate ? 1 : 0)

  useEffect(() => {
    if (!value) {
      setFiltered([])
      setShowDropdown(false)
      return
    }
    const lower = value.toLowerCase()
    const matches = people.filter(
      p =>
        p.title.toLowerCase().includes(lower) &&
        !existingPeople.some(e => e.toLowerCase() === p.title.toLowerCase())
    )
    setFiltered(matches)
    setShowDropdown(true)
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
    onAdd(person.title)
    setValue('')
    setShowDropdown(false)
  }

  const handleCreate = async () => {
    const name = trimmed
    if (!name || creating) return
    setCreating(true)
    try {
      await fetch(getAPI() + '/persons', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      onAdd(name)
      setValue('')
      setShowDropdown(false)
    } catch {
      // caller handles error display
    } finally {
      setCreating(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' && showDropdown && totalItems > 0) {
      e.preventDefault()
      setHighlightIndex(i => (i + 1) % totalItems)
    } else if (e.key === 'ArrowUp' && showDropdown && totalItems > 0) {
      e.preventDefault()
      setHighlightIndex(i => (i - 1 + totalItems) % totalItems)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (showDropdown && highlightIndex >= 0 && highlightIndex < filtered.length) {
        select(filtered[highlightIndex])
      } else if (showDropdown && showCreate && highlightIndex === filtered.length) {
        handleCreate()
      } else if (trimmed) {
        if (filtered.length > 0) {
          select(filtered[0])
        } else {
          handleCreate()
        }
      }
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
        placeholder="Search or create person…"
        className="text-xs h-7 w-48"
        autoFocus
        disabled={creating}
      />
      {showDropdown && totalItems > 0 && (
        <ul className="absolute z-50 mt-1 w-52 bg-popover border border-border rounded-md shadow-md max-h-[160px] overflow-auto">
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
          {showCreate && (
            <li
              className={cn(
                "px-3 py-1.5 text-sm cursor-pointer text-muted-foreground italic",
                highlightIndex === filtered.length && "bg-accent text-accent-foreground"
              )}
              onMouseDown={handleCreate}
            >
              {creating ? 'Creating…' : `Create "${trimmed}"`}
            </li>
          )}
        </ul>
      )}
    </div>
  )
}
