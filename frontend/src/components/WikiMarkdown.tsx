import { useCallback } from 'react'
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useNoteContext } from '@/contexts/NoteContext'
import { useUIContext } from '@/contexts/UIContext'
import type { Components } from 'react-markdown'

// Pre-process body: replace [[ref]] with [ref](wiki:encoded) so
// ReactMarkdown treats them as links the custom renderer can intercept.
// ref can be a note title OR an absolute file path.
function preprocessWikiLinks(body: string): string {
  return body.replace(/\[\[([^\]]+)\]\]/g, (_match, ref: string) => {
    const encoded = encodeURIComponent(ref)
    return `[${ref}](wiki:${encoded})`
  })
}

// Pass wiki: URLs through; let defaultUrlTransform handle everything else.
function urlTransform(url: string): string {
  if (url.startsWith('wiki:')) return url
  return defaultUrlTransform(url)
}

interface Props {
  children: string
  className?: string
}

export function WikiMarkdown({ children, className }: Props) {
  const { notes, openNote } = useNoteContext()
  const { setCurrentView } = useUIContext()

  const buildMaps = useCallback(() => {
    const byTitle = new Map<string, string>()   // lowercased title → path
    const byRelPath = new Map<string, string>() // relative path → title
    const byAbsPath = new Map<string, string>() // absolute path → title (pre-Phase-32 notes)
    for (const n of notes) {
      byTitle.set(n.title.toLowerCase(), n.path)
      if (n.path.startsWith('/')) {
        byAbsPath.set(n.path, n.title)
      } else {
        byRelPath.set(n.path, n.title)
      }
    }
    return { byTitle, byRelPath, byAbsPath }
  }, [notes])

  const resolveAbsPath = useCallback((absRef: string) => {
    // Returns { path, title } for an absolute wiki-link ref, or null if not found.
    const { byRelPath, byAbsPath } = buildMaps()

    // Exact match on absolute path (pre-Phase-32 notes stored with abs path)
    const absTitle = byAbsPath.get(absRef)
    if (absTitle) return { path: absRef, title: absTitle }

    // Suffix match: API returns relative paths; wiki-links embed absolute paths.
    // Find the note whose relative path is a suffix of the absolute ref.
    for (const [relPath, title] of byRelPath) {
      if (absRef.endsWith('/' + relPath)) {
        // Reconstruct the path to pass to openNote — use relative since that's
        // what the backend expects.
        return { path: relPath, title }
      }
    }
    return null
  }, [buildMaps])

  const markdownComponents: Components = {
    a({ href, children }) {
      if (href?.startsWith('wiki:')) {
        const ref = decodeURIComponent(href.slice(5))
        const { byTitle } = buildMaps()

        // Path-based: [[/absolute/path/to/note.md]]
        if (ref.startsWith('/')) {
          const found = resolveAbsPath(ref)
          if (found) {
            return (
              <button
                className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors cursor-pointer"
                onClick={() => { setCurrentView('notes'); openNote(found.path) }}
                title={`Go to: ${found.title}`}
              >
                {found.title}
              </button>
            )
          }
          // Not in index (deleted or not yet loaded) — show filename only
          const filename = ref.split('/').pop()?.replace(/\.md$/, '') ?? ref
          return (
            <span
              className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground opacity-50"
              title={`No note found: ${ref}`}
            >
              {filename}
            </span>
          )
        }

        // Title-based: [[Note Title]]
        const targetPath = byTitle.get(ref.toLowerCase())
        if (targetPath) {
          return (
            <button
              className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors cursor-pointer"
              onClick={() => { setCurrentView('notes'); openNote(targetPath) }}
              title={`Go to: ${ref}`}
            >
              {children}
            </button>
          )
        }
        return (
          <span
            className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground opacity-50"
            title={`No note found: ${ref}`}
          >
            {children}
          </span>
        )
      }
      // Regular link
      return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
    },
  }

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={markdownComponents}
        urlTransform={urlTransform}
      >
        {preprocessWikiLinks(children)}
      </ReactMarkdown>
    </div>
  )
}
