import { useState, useEffect } from 'react'
import { Paperclip, Upload } from 'lucide-react'
import { getAPI } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import type { Attachment } from '@/types'

interface Props {
  notePath: string
  refreshTick?: number
  onUploadClick?: () => void
}

export function AttachmentsSection({ notePath, refreshTick = 0, onUploadClick }: Props) {
  const [attachments, setAttachments] = useState<Attachment[]>([])

  useEffect(() => {
    if (!notePath) return
    fetch(`${getAPI()}/notes/attachments?path=${encodeURIComponent(notePath)}`)
      .then(r => r.json())
      .then(d => setAttachments(d.attachments ?? []))
      .catch(() => setAttachments([]))
  }, [notePath, refreshTick])

  return (
    <div className="mt-4 pt-3 border-t border-border" data-testid="attachment-list">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1 text-xs font-semibold uppercase text-muted-foreground">
          <Paperclip className="h-3 w-3" />
          Attachments
        </div>
        {onUploadClick && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={onUploadClick}
          >
            <Upload className="h-3 w-3 mr-1" />
            Upload
          </Button>
        )}
      </div>
      {attachments.length === 0 ? (
        <p className="text-xs text-muted-foreground">No attachments yet</p>
      ) : (
        <ul className="space-y-0.5">
          {attachments.map(a => (
            <li key={a.filename} className="text-xs text-muted-foreground truncate">
              <a
                href={a.file_path}
                target="_blank"
                rel="noreferrer"
                className="hover:text-foreground hover:underline"
              >
                {a.filename}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
