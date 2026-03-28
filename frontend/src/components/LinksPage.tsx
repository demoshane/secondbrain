import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Link, ExternalLink, Trash2 } from 'lucide-react'
import { cn, getAPI, encodePath } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/ui/empty-state'
import { SkeletonList } from '@/components/ui/skeleton-list'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { toast } from 'sonner'

interface LinkSummary {
  path: string
  title: string
  url: string
  domain: string
  date: string
  tags: string
  description: string
}

interface LinkDetail {
  path: string
  title: string
  url: string
  domain: string
  body: string
  date: string
  tags: string
}

function parseTags(raw: string): string[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function LinksPage() {
  const [links, setLinks] = useState<LinkSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedLink, setSelectedLink] = useState<LinkSummary | null>(null)
  const [linkDetail, setLinkDetail] = useState<LinkDetail | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [tagFilter, setTagFilter] = useState('')
  const [pendingDelete, setPendingDelete] = useState<LinkSummary | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetch(`${getAPI()}/links`)
      .then(r => r.json())
      .then(d => { setLinks(d.links ?? []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedLink) { setLinkDetail(null); return }
    const enc = encodePath(selectedLink.path)
    fetch(`${getAPI()}/links/${enc}`)
      .then(r => r.json())
      .then(d => setLinkDetail(d))
      .catch(() => {})
  }, [selectedLink])

  const filtered = links
    .filter(l =>
      l.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (l.description ?? '').toLowerCase().includes(searchQuery.toLowerCase())
    )
    .filter(l => !tagFilter || parseTags(l.tags).includes(tagFilter))

  const hasActiveFilter = searchQuery.length > 0 || tagFilter.length > 0

  const confirmDelete = async () => {
    if (!pendingDelete || deleting) return
    setDeleting(true)
    try {
      const enc = encodePath(pendingDelete.path)
      const res = await fetch(`${getAPI()}/notes/${enc}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Delete failed')
      setLinks(prev => prev.filter(l => l.path !== pendingDelete.path))
      if (selectedLink?.path === pendingDelete.path) {
        setSelectedLink(null)
        setLinkDetail(null)
      }
      setPendingDelete(null)
      toast.success('Link deleted')
    } catch {
      toast.error('Delete failed. Try again or check the app logs.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden" data-testid="links-page">
      {/* List column */}
      <div className="w-80 border-r border-border bg-card flex flex-col overflow-hidden">
        <div className="p-3 border-b border-border flex-shrink-0">
          <Input
            placeholder="Search links..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="text-sm h-8"
          />
          {tagFilter && (
            <div className="flex items-center gap-1 mt-2">
              <span className="text-xs text-muted-foreground">Tag:</span>
              <Badge
                variant="secondary"
                className="text-xs cursor-pointer"
                onClick={() => setTagFilter('')}
              >
                {tagFilter} ×
              </Badge>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <SkeletonList count={5} rowHeight="h-14" className="p-2" />
          ) : filtered.length === 0 ? (
            <div className="flex items-center justify-center h-32 px-4 text-center">
              <p className="text-sm text-muted-foreground">
                {hasActiveFilter
                  ? 'No links match your filter'
                  : 'No links saved yet'}
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {filtered.map(link => {
                const tags = parseTags(link.tags)
                return (
                  <li
                    key={link.path}
                    className={cn(
                      'px-3 py-2 cursor-pointer hover:bg-secondary/30 transition-colors',
                      selectedLink?.path === link.path && 'bg-secondary'
                    )}
                    onClick={() => setSelectedLink(link)}
                  >
                    <div className="flex items-baseline justify-between gap-1">
                      <span className="font-medium text-sm text-foreground truncate flex-1">{link.title}</span>
                      <span className="text-xs text-muted-foreground flex-shrink-0">{link.date}</span>
                    </div>
                    <div className="text-xs text-muted-foreground truncate">{link.domain}</div>
                    {link.description && (
                      <div className="text-xs text-muted-foreground truncate mt-0.5">
                        {link.description}
                      </div>
                    )}
                    {tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {tags.map(tag => (
                          <Badge
                            key={tag}
                            variant="outline"
                            className="text-xs cursor-pointer hover:bg-accent px-1 py-0"
                            onClick={e => { e.stopPropagation(); setTagFilter(tag) }}
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>

      {/* Detail column */}
      <div className="flex-1 bg-background overflow-y-auto">
        {loading && !selectedLink ? null : !selectedLink ? (
          links.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <EmptyState
                icon={Link}
                heading="No saved links"
                body="Save web links from the Chrome extension or via capture."
              />
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <EmptyState
                icon={Link}
                heading="Select a link"
                body="Choose a saved link to view its content and metadata."
              />
            </div>
          )
        ) : (
          <div>
            {/* Detail header */}
            <div className="flex items-start justify-between gap-3 px-6 py-4 border-b border-border">
              <div className="flex-1 min-w-0">
                <h2 className="text-lg font-semibold text-foreground leading-tight">
                  {linkDetail?.title ?? selectedLink.title}
                </h2>
                <div className="flex items-center gap-2 mt-1">
                  <a
                    href={linkDetail?.url ?? selectedLink.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline truncate"
                    onClick={e => e.stopPropagation()}
                  >
                    {linkDetail?.domain ?? selectedLink.domain}
                  </a>
                  <span className="text-xs text-muted-foreground">·</span>
                  <span className="text-xs text-muted-foreground">{linkDetail?.date ?? selectedLink.date}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => window.open(linkDetail?.url ?? selectedLink.url, '_blank', 'noopener')}
                >
                  <ExternalLink className="h-4 w-4 mr-1" />
                  Visit Link
                </Button>
                <button
                  type="button"
                  onClick={() => setPendingDelete(selectedLink)}
                  className="p-2 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
                  aria-label="Delete link"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Tags row */}
            {parseTags(linkDetail?.tags ?? selectedLink.tags).length > 0 && (
              <div className="flex flex-wrap gap-1 px-6 py-3 border-b border-border">
                {parseTags(linkDetail?.tags ?? selectedLink.tags).map(tag => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}

            {/* Body */}
            {linkDetail?.body && (
              <div className="px-6 py-4">
                <div className="prose prose-sm prose-invert max-w-none">
                  <Markdown remarkPlugins={[remarkGfm]}>{linkDetail.body}</Markdown>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        title={`Delete '${pendingDelete?.title ?? 'this link'}'?`}
        description="This cannot be undone."
        confirmLabel={deleting ? 'Deleting...' : 'Delete'}
        cancelLabel="Keep"
        variant="destructive"
      />
    </div>
  )
}
