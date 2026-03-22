import { useState } from 'react'
import { toast } from 'sonner'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { getAPI } from '@/lib/utils'

interface NewEntityModalProps {
  open: boolean
  onClose: () => void
  entityType: 'people' | 'meetings' | 'projects'
  onCreated: () => void
}

function titleFor(entityType: NewEntityModalProps['entityType']): string {
  if (entityType === 'people') return 'New Person'
  if (entityType === 'meetings') return 'New Meeting'
  return 'New Project'
}

export function NewEntityModal({ open, onClose, entityType, onCreated }: NewEntityModalProps) {
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [creating, setCreating] = useState(false)

  const handleClose = () => {
    setName('')
    setRole('')
    onClose()
  }

  const handleCreate = async () => {
    if (!name.trim() || creating) return
    setCreating(true)
    try {
      const body: Record<string, string> = { name: name.trim() }
      if (entityType === 'people' && role.trim()) {
        body.role = role.trim()
      }
      const resp = await fetch(`${getAPI()}/${entityType}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      toast.success(`${name.trim()} created`)
      onCreated()
      handleClose()
    } catch {
      toast.error('Something went wrong — try again')
    } finally {
      setCreating(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && handleClose()}>
      <DialogContent data-testid="new-entity-modal">
        <DialogHeader>
          <DialogTitle>{titleFor(entityType)}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input
            placeholder="Name"
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !creating && name.trim() && handleCreate()}
            data-testid="new-entity-name"
            autoFocus
          />
          {entityType === 'people' && (
            <Input
              placeholder="Role / title (optional)"
              value={role}
              onChange={e => setRole(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !creating && name.trim() && handleCreate()}
              data-testid="new-entity-role"
            />
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={handleClose}>
              Discard
            </Button>
            <Button
              disabled={!name.trim() || creating}
              onClick={handleCreate}
              data-testid="new-entity-submit"
            >
              {creating ? 'Creating...' : 'Create'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
