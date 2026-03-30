import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { getAPI } from "@/lib/utils"
import { toast } from "sonner"
import type { ActionItem } from "@/types"

interface ActionDetailModalProps {
  action: ActionItem | null
  open: boolean
  onClose: () => void
  onSaved: (updated: ActionItem) => void
}

export function ActionDetailModal({ action, open, onClose, onSaved }: ActionDetailModalProps) {
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (action) {
      setTitle(action.text)
      setDescription(action.description ?? "")
    }
  }, [action])

  const handleSave = async () => {
    if (!action || !title.trim() || saving) return
    setSaving(true)
    try {
      const res = await fetch(`${getAPI()}/actions/${action.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: title.trim(), description: description || null }),
      })
      if (!res.ok) throw new Error()
      toast.success("Action updated")
      onSaved({ ...action, text: title.trim(), description: description || null })
      onClose()
    } catch {
      toast.error("Failed to save. Try again.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Action Detail</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4 mt-2">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Title</label>
            <input
              autoFocus
              value={title}
              onChange={e => setTitle(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSave() }}
              className="rounded-md border border-input bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSave() }}
              placeholder="Add more context, notes, or steps…"
              rows={5}
              className="rounded-md border border-input bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring resize-y"
            />
          </div>
          <div className="flex items-center gap-2 justify-end">
            <span className="text-xs text-muted-foreground mr-auto">Cmd+Enter to save</span>
            <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
            <Button size="sm" onClick={handleSave} disabled={saving || !title.trim()}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
