import { createContext, useContext, useState, useCallback } from 'react'
import { getAPI } from '@/lib/utils'
import type { Note } from '@/types'

interface SearchContextValue {
  query: string
  mode: 'hybrid' | 'bm25' | 'semantic'
  results: Note[] | null
  tagFilter: string | null
  setQuery: (q: string) => void
  setMode: (m: 'hybrid' | 'bm25' | 'semantic') => void
  setTagFilter: (t: string | null) => void
  search: (q: string, mode?: 'hybrid' | 'bm25' | 'semantic', tag?: string | null) => Promise<void>
  clearSearch: () => void
}

const SearchContext = createContext<SearchContextValue>(null!)
export const useSearchContext = () => useContext(SearchContext)

export function SearchProvider({ children }: { children: React.ReactNode }) {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<'hybrid' | 'bm25' | 'semantic'>('hybrid')
  const [results, setResults] = useState<Note[] | null>(null)
  const [tagFilter, setTagFilterRaw] = useState<string | null>(null)

  // Clicking a tag clears any active search results so the full notes list is used
  const setTagFilter = useCallback((t: string | null) => {
    setTagFilterRaw(t)
    if (t !== null) setResults(null)
  }, [])

  const search = useCallback(async (q: string, m = mode, tag = tagFilter) => {
    const body: Record<string, unknown> = { query: q, mode: m }
    if (tag) body.tag = tag
    const res = await fetch(`${getAPI()}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    setResults(data.results ?? [])
  }, [mode, tagFilter])

  const clearSearch = useCallback(() => {
    setQuery('')
    setResults(null)
    setTagFilterRaw(null)
  }, [])

  return (
    <SearchContext.Provider value={{ query, mode, results, tagFilter, setQuery, setMode, setTagFilter, search, clearSearch }}>
      {children}
    </SearchContext.Provider>
  )
}
