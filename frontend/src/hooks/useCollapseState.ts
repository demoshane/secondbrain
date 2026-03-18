import { useState, useEffect, useCallback } from 'react'
import { getAPI } from '@/lib/utils'
import type { CollapsePrefs } from '@/types'

export function useCollapseState() {
  const [prefs, setPrefs] = useState<CollapsePrefs>({})

  useEffect(() => {
    fetch(`${getAPI()}/ui/prefs`)
      .then(r => r.json())
      .then(data => setPrefs(data ?? {}))
      .catch(() => {})
  }, [])

  const toggle = useCallback((key: string) => {
    setPrefs(prev => {
      const next = { ...prev, [key]: !prev[key] }
      fetch(`${getAPI()}/ui/prefs`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(next),
      }).catch(() => {})
      return next
    })
  }, [])

  return { prefs, toggle }
}
