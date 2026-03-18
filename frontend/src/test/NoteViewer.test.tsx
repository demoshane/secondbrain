import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { NoteViewer } from '@/components/NoteViewer'
import { NoteProvider } from '@/contexts/NoteContext'
import { SearchProvider } from '@/contexts/SearchContext'
import type { Note } from '@/types'
import React from 'react'

const mockNote: Note = {
  path: '/brain/ideas/test.md',
  title: 'Hello World',
  type: 'idea',
  body: '# Hello\n\nThis is **bold** text.',
  tags: ['react', 'test'],
  people: [],
  folder: 'ideas',
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <NoteProvider>
      <SearchProvider>{children}</SearchProvider>
    </NoteProvider>
  )
}

describe('NoteViewer', () => {
  it('renders markdown as HTML — h1 present, no raw # character', () => {
    const { getByTestId, queryByText } = render(
      <Wrapper><NoteViewer note={mockNote} /></Wrapper>
    )
    const body = getByTestId('note-body')
    // Should have an h1 element
    expect(body.querySelector('h1')).not.toBeNull()
    // h1 text should be "Hello"
    expect(body.querySelector('h1')?.textContent).toBe('Hello')
    // Raw # should not be visible as text
    expect(queryByText('# Hello')).toBeNull()
    // bold text rendered as <strong>
    expect(body.querySelector('strong')).not.toBeNull()
  })

  it('renders tag chips for each tag', () => {
    const { getByTestId } = render(
      <Wrapper><NoteViewer note={mockNote} /></Wrapper>
    )
    expect(getByTestId('tag-react')).not.toBeNull()
    expect(getByTestId('tag-test')).not.toBeNull()
  })
})
