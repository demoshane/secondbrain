import React, { useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import App from './App'
import { NoteProvider } from './contexts/NoteContext'
import { SearchProvider } from './contexts/SearchContext'
import { UIProvider } from './contexts/UIContext'
import { SSEProvider } from './contexts/SSEContext'

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

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <NoteProvider>
        <SearchProvider>
          <UIProvider>
            <SSEProvider>
              <App />
            </SSEProvider>
          </UIProvider>
        </SearchProvider>
      </NoteProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
