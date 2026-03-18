import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from '@testing-library/react'
import React, { useEffect } from 'react'

function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const apply = (e: MediaQueryList | MediaQueryListEvent) => {
      document.documentElement.classList.toggle('dark', e.matches)
    }
    apply(mq)
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])
  return <>{children}</>
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('dark')
  })

  it('adds dark class to html when prefers-color-scheme is dark', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    })
    render(<ThemeProvider><div /></ThemeProvider>)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })
})
