import { useCallback } from 'react'
import { getAPI, encodePath } from '@/lib/utils'

export function useNoteActions() {
  const saveNote = useCallback(async (path: string, body: string, title?: string) => {
    const encoded = encodePath(path)
    const payload = title !== undefined
      ? { title_and_body_title: title, title_and_body_body: body }
      : { body }
    const res = await fetch(`${getAPI()}/notes/${encoded}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.ok
  }, [])

  const deleteNote = useCallback(async (path: string) => {
    const encoded = encodePath(path)
    const res = await fetch(`${getAPI()}/notes/${encoded}`, { method: 'DELETE' })
    return res.ok
  }, [])

  const createNote = useCallback(async (title: string, noteType: string) => {
    const res = await fetch(`${getAPI()}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, type: noteType }),
    })
    if (!res.ok) return null
    return res.json()
  }, [])

  return { saveNote, deleteNote, createNote }
}
