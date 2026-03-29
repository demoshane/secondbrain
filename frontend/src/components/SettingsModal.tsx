import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2, Settings, X } from 'lucide-react'
import { getAPI } from '@/lib/utils'

interface Routing {
  public_model: string
  private_model: string
  pii_model: string
  fallback_model: string
}

interface Config {
  routing: Routing
  ollama: { host: string }
  models: Record<string, { adapter: string; model: string }>
}

interface Props {
  open: boolean
  onClose: () => void
}

const FIELD_LABELS: Record<keyof Routing, string> = {
  public_model: 'Public notes model',
  private_model: 'Private notes model',
  pii_model: 'PII notes model',
  fallback_model: 'Fallback model',
}

const DEFAULT_MARKERS = ['TODO', 'AP', 'action:', '@owner', 'Action Point']

const FIELD_DESCRIPTIONS: Record<keyof Routing, string> = {
  public_model: 'Used for non-sensitive content — recap, synthesis, Ask Brain',
  private_model: 'Used for private (non-PII) notes',
  pii_model: 'Used for PII-flagged notes — stays local',
  fallback_model: 'Fallback if the primary model fails (e.g. Claude quota exceeded)',
}

export function SettingsModal({ open, onClose }: Props) {
  const [config, setConfig] = useState<Config | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [customMarkers, setCustomMarkers] = useState<string[]>([])
  const [newMarker, setNewMarker] = useState('')

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    setSaved(false)
    setNewMarker('')
    fetch(`${getAPI()}/config`)
      .then(r => r.json())
      .then((data: Config) => setConfig(data))
      .catch(() => setError('Could not load config.'))
      .finally(() => setLoading(false))
    fetch(`${getAPI()}/config/action-item-markers`)
      .then(r => r.json())
      .then(data => setCustomMarkers(data.custom_markers || []))
      .catch(() => {}) // Non-fatal — defaults still shown
  }, [open])

  const modelOptions = config ? Object.keys(config.models) : []

  const setRouting = (key: keyof Routing, value: string) => {
    if (!config) return
    setConfig({ ...config, routing: { ...config.routing, [key]: value } })
    setSaved(false)
  }

  const setOllamaHost = (value: string) => {
    if (!config) return
    setConfig({ ...config, ollama: { host: value } })
    setSaved(false)
  }

  const isDuplicate = [...DEFAULT_MARKERS, ...customMarkers].some(
    m => m.toLowerCase() === newMarker.trim().toLowerCase()
  )

  const handleAddMarker = () => {
    if (!newMarker.trim() || isDuplicate) return
    setCustomMarkers(prev => [...prev, newMarker.trim()])
    setNewMarker('')
    setSaved(false)
  }

  const handleSave = async () => {
    if (!config) return
    setSaving(true)
    setError(null)
    try {
      const [res] = await Promise.all([
        fetch(`${getAPI()}/config`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ routing: config.routing, ollama: config.ollama }),
        }),
        fetch(`${getAPI()}/config/action-item-markers`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ custom_markers: customMarkers }),
        }),
      ])
      const data = await res.json()
      if (!res.ok) { setError(data.error || 'Save failed'); return }
      setSaved(true)
    } catch {
      setError('Could not reach the API.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        {config && !loading && (
          <div className="space-y-6 mt-2">
            {/* AI model routing */}
            <div>
              <p className="text-sm font-medium mb-3">AI model routing</p>
              <div className="space-y-4">
                {(Object.keys(FIELD_LABELS) as (keyof Routing)[]).map(key => (
                  <div key={key}>
                    <label className="text-xs font-medium text-foreground">{FIELD_LABELS[key]}</label>
                    <p className="text-xs text-muted-foreground mb-1.5">{FIELD_DESCRIPTIONS[key]}</p>
                    <Select value={config.routing[key]} onValueChange={v => setRouting(key, v)}>
                      <SelectTrigger className="h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {modelOptions.map(m => (
                          <SelectItem key={m} value={m}>{m}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </div>
            </div>

            {/* Ollama */}
            <div>
              <p className="text-sm font-medium mb-3">Ollama</p>
              <div>
                <label className="text-xs font-medium text-foreground">Host URL</label>
                <p className="text-xs text-muted-foreground mb-1.5">
                  Where your local Ollama instance is running
                </p>
                <Input
                  value={config.ollama.host}
                  onChange={e => setOllamaHost(e.target.value)}
                  className="h-8 font-mono text-sm"
                  placeholder="http://localhost:11434"
                />
              </div>
            </div>

            {/* Capture */}
            <div>
              <p className="text-sm font-semibold mb-3">Capture</p>
              <div>
                <label className="text-xs font-semibold text-foreground">Action-item markers</label>
                <p className="text-xs text-muted-foreground mb-2">Keywords that flag a line as an action item during smart capture</p>
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {DEFAULT_MARKERS.map(m => (
                    <span key={m} className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-secondary border border-border text-muted-foreground" title="Default marker — cannot be removed">
                      {m}
                    </span>
                  ))}
                  {customMarkers.map(m => (
                    <span key={m} className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-secondary border border-border text-foreground">
                      {m}
                      <button onClick={() => { setCustomMarkers(prev => prev.filter(x => x !== m)); setSaved(false) }} className="hover:text-destructive" aria-label={`Remove marker ${m}`}>
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input
                    value={newMarker}
                    onChange={e => setNewMarker(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleAddMarker() }}
                    placeholder="Add marker..."
                    className={`h-8 flex-1 ${isDuplicate && newMarker.trim() ? 'border-destructive' : ''}`}
                  />
                  <Button size="sm" onClick={handleAddMarker} disabled={!newMarker.trim() || isDuplicate}>Add</Button>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              {saved && <span className="text-xs text-green-500">Saved</span>}
              <Button onClick={handleSave} disabled={saving} size="sm">
                {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                Save
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
