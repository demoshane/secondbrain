import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { getAPI } from '@/lib/utils'

interface DeleteEntityModalProps {
  open: boolean
  onClose: () => void
  entityType: 'persons' | 'meetings' | 'projects'
  entityName: string
  entityPath: string
  onDeleted: () => void
}

function keepLabel(entityType: DeleteEntityModalProps['entityType']): string {
  if (entityType === 'persons') return 'Keep Person'
  if (entityType === 'meetings') return 'Keep Meeting'
  return 'Keep Project'
}

interface LinkCounts {
  meeting_count: number
  action_count: number
}

export function DeleteEntityModal({
  open,
  onClose,
  entityType,
  entityName,
  entityPath,
  onDeleted,
}: DeleteEntityModalProps) {
  const [deleting, setDeleting] = useState(false)
  const [linkCounts, setLinkCounts] = useState<LinkCounts | null>(null)

  // Fetch link counts when modal opens (people only)
  useEffect(() => {
    if (!open || !entityPath) {
      setLinkCounts(null)
      return
    }
    if (entityType !== 'persons') {
      setLinkCounts(null)
      return
    }
    const relPath = entityPath.startsWith('/') ? entityPath.slice(1) : entityPath
    fetch(`${getAPI()}/persons/${relPath}/links`)
      .then(r => r.ok ? r.json() : null)
      .then((data: LinkCounts | null) => setLinkCounts(data))
      .catch(() => setLinkCounts(null))
  }, [open, entityPath, entityType])

  const handleDelete = async () => {
    if (deleting) return
    setDeleting(true)
    try {
      const relPath = entityPath.startsWith('/') ? entityPath.slice(1) : entityPath
      const resp = await fetch(
        `${getAPI()}/${entityType}/${relPath}`,
        { method: 'DELETE' }
      )
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      toast.success(`${entityName} deleted`)
      onDeleted()
      onClose()
    } catch {
      toast.error('Something went wrong — try again')
    } finally {
      setDeleting(false)
    }
  }

  const hasCascade =
    entityType === 'persons' &&
    linkCounts !== null &&
    (linkCounts.meeting_count > 0 || linkCounts.action_count > 0)

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent data-testid="delete-entity-modal">
        <DialogHeader>
          <DialogTitle>Delete {entityName}?</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          {hasCascade ? (
            <p className="text-sm text-muted-foreground" data-testid="cascade-warning">
              {linkCounts!.meeting_count > 0 && (
                <span>{linkCounts!.meeting_count} note{linkCounts!.meeting_count !== 1 ? 's' : ''} mention this person. </span>
              )}
              {linkCounts!.action_count > 0 && (
                <span>{linkCounts!.action_count} action item{linkCounts!.action_count !== 1 ? 's' : ''} are assigned to them. </span>
              )}
              <span>This cannot be undone.</span>
            </p>
          ) : (
            <p className="text-sm text-muted-foreground" data-testid="no-cascade-warning">
              This cannot be undone.
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose} data-testid="delete-entity-keep">
              {keepLabel(entityType)}
            </Button>
            <Button
              variant="destructive"
              disabled={deleting}
              onClick={handleDelete}
              data-testid="delete-entity-confirm"
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
