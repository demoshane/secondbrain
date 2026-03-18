import { describe, it, expect } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { UIProvider, useUIContext } from '@/contexts/UIContext'
import { TabBar } from '@/components/TabBar'
function ReadView() {
  const { currentView } = useUIContext()
  return <span data-testid="view">{currentView}</span>
}

describe('TabBar', () => {
  it('switches to actions view when Action Items tab is clicked', () => {
    const { getByTestId } = render(
      <UIProvider>
        <TabBar />
        <ReadView />
      </UIProvider>
    )
    expect(getByTestId('view').textContent).toBe('notes')
    fireEvent.click(getByTestId('tab-actions'))
    expect(getByTestId('view').textContent).toBe('actions')
  })
})
