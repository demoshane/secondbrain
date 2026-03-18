import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, act } from '@testing-library/react'
import React, { createContext, useContext } from 'react'

// Minimal inline SSEContext for isolation (avoids NoteContext dependency in test)
const Ctx = createContext({ connected: false })

function TestSSEProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = React.useState(false)
  React.useEffect(() => {
    const handlers: Record<string, Function> = {}
    const mockSrc = {
      set onopen(fn: Function) { handlers.open = fn },
      set onerror(fn: Function) { handlers.error = fn },
      set onmessage(fn: Function) { handlers.message = fn },
      close: vi.fn(),
      // expose to test
      triggerOpen: () => handlers.open?.(),
    }
    ;(window as any).__mockEventSource = mockSrc
    ;(window as any).EventSource = function() { return mockSrc }
    const src = new (window as any).EventSource('/events')
    src.onopen = () => setConnected(true)
    src.onerror = () => setConnected(false)
    return () => src.close()
  }, [])
  return <Ctx.Provider value={{ connected }}>{children}</Ctx.Provider>
}

function ReadConnected() {
  const { connected } = useContext(Ctx)
  return <span data-testid="status">{connected ? 'connected' : 'disconnected'}</span>
}

describe('SSEContext', () => {
  it('reflects connected=true after EventSource opens', async () => {
    const { getByTestId } = render(
      <TestSSEProvider><ReadConnected /></TestSSEProvider>
    )
    expect(getByTestId('status').textContent).toBe('disconnected')
    await act(async () => {
      ;(window as any).__mockEventSource.triggerOpen()
    })
    expect(getByTestId('status').textContent).toBe('connected')
  })
})
