import { useState, useEffect } from 'react'
import { cn, getAPI, encodePath } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ExternalLink } from 'lucide-react'

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
  const [selectedLink, setSelectedLink] = useState<LinkSummary | null>(null)
  const [linkDetail, setLinkDetail] = useState<LinkDetail | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [tagFilter, setTagFilter] = useState('')

  useEffect(() => {
    fetch(`${getAPI()}/links`)
      .then(r => r.json())
      .then(d => setLinks(d.links ?? []))
      .catch(() => {})
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

  return (
    <div className="flex h-full" data-testid="links-page">
      {/* Left column — link list */}
      <div className="w-80 border-r overflow-y-auto flex flex-col flex-shrink-0">
        <div className="p-2 border-b">
          <Input
            placeholder="Search links..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="text-sm"
          />
          {tagFilter && (
            <div className="flex items-center gap-1 mt-1">
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
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-sm text-muted-foreground px-4 text-center">
              {hasActiveFilter
                ? 'No links match your filter'
                : 'No links saved yet — use sb_capture_link in Claude'}
            </div>
          ) : (
            <ul className="divide-y">
              {filtered.map(link => {
                const tags = parseTags(link.tags)
                return (
                  <li
                    key={link.path}
                    className={cn(
                      'px-3 py-2 cursor-pointer hover:bg-accent',
                      selectedLink?.path === link.path && 'bg-muted'
                    )}
                    onClick={() => setSelectedLink(link)}
                  >
                    <div className="flex items-baseline justify-between gap-1">
                      <span className="font-medium text-sm truncate flex-1">{link.title}</span>
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

      {/* Right column — detail panel */}
      <div className="flex-1 overflow-y-auto">
        {!selectedLink ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            Select a link to view details
          </div>
        ) : (
          <div>
            <div className="flex items-start justify-between gap-3 px-4 py-3 border-b">
              <div className="flex-1 min-w-0">
                <h2 className="text-lg font-semibold leading-tight">{linkDetail?.title ?? selectedLink.title}</h2>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-sm text-muted-foreground">{linkDetail?.domain ?? selectedLink.domain}</span>
                  <span className="text-xs text-muted-foreground">·</span>
                  <span className="text-xs text-muted-foreground">{linkDetail?.date ?? selectedLink.date}</span>
                </div>
              </div>
              <Button
                size="sm"
                variant="default"
                className="flex-shrink-0"
                onClick={() => window.open(linkDetail?.url ?? selectedLink.url, '_blank', 'noopener')}
              >
                <ExternalLink className="h-4 w-4 mr-1" />
                Visit Link
              </Button>
            </div>

            {parseTags(linkDetail?.tags ?? selectedLink.tags).length > 0 && (
              <div className="flex flex-wrap gap-1 px-4 py-2 border-b">
                {parseTags(linkDetail?.tags ?? selectedLink.tags).map(tag => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}

            {linkDetail?.body && (
              <div className="px-4 py-3">
                <pre className="text-sm whitespace-pre-wrap font-sans text-foreground leading-relaxed">
                  {linkDetail.body}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
