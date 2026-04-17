import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Loader2, Settings, X, CheckCircle2, XCircle } from 'lucide-react'
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

interface PersonOption {
  path: string
  title: string
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

const GROQ_FEATURES = [
  { key: 'ask_brain', label: 'Ask Brain', desc: 'Route brain queries to Groq' },
  { key: 'enrich', label: 'Note enrichment', desc: 'AI-merge content into existing notes via Groq (non-PII only)' },
  { key: 'followup_questions', label: 'Follow-up questions', desc: 'Generate follow-up prompts via Groq' },
  { key: 'digest', label: 'Weekly digest', desc: 'Synthesise your digest using Groq' },
  { key: 'person_synthesis', label: 'Person insights', desc: 'Generate people context via Groq' },
] as const

export function SettingsModal({ open, onClose }: Props) {
  const [config, setConfig] = useState<Config | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [customMarkers, setCustomMarkers] = useState<string[]>([])
  const [newMarker, setNewMarker] = useState('')
  const [mePath, setMePath] = useState<string>('')
  const [persons, setPersons] = useState<PersonOption[]>([])

  // Groq / AI Provider state
  const [groqConfigured, setGroqConfigured] = useState(false)
  const [groqKey, setGroqKey] = useState('')
  const [savingKey, setSavingKey] = useState(false)
  const [testResult, setTestResult] = useState<{ok: boolean; error: string | null} | null>(null)
  const [testingConnection, setTestingConnection] = useState(false)
  const [allLocal, setAllLocal] = useState(false)
  const [groqToggles, setGroqToggles] = useState({
    ask_brain: false, enrich: false, followup_questions: false, digest: false, person_synthesis: false,
  })

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
    fetch(`${getAPI()}/config/me`)
      .then(r => r.json())
      .then(data => setMePath(data.identity || ''))
      .catch(() => {})
    fetch(`${getAPI()}/persons`)
      .then(r => r.json())
      .then(data => setPersons(data.people || []))
      .catch(() => {})
    fetch(`${getAPI()}/config/groq`)
      .then(r => r.json())
      .then(data => setGroqConfigured(data.configured))
      .catch(() => {})
    fetch(`${getAPI()}/config/groq-settings`)
      .then(r => r.json())
      .then(data => {
        setAllLocal(data.all_local || false)
        setGroqToggles({
          ask_brain: data.groq?.ask_brain || false,
          enrich: data.groq?.enrich || false,
          followup_questions: data.groq?.followup_questions || false,
          digest: data.groq?.digest || false,
          person_synthesis: data.groq?.person_synthesis || false,
        })
      })
      .catch(() => {})
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

  const handleSaveGroqKey = async () => {
    setSavingKey(true)
    setTestResult(null)
    try {
      const res = await fetch(`${getAPI()}/config/groq`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: groqKey }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.error || 'Save failed'); return }
      setGroqConfigured(true)
      setGroqKey('')
      // Auto-test connectivity
      setTestingConnection(true)
      try {
        const testRes = await fetch(`${getAPI()}/config/groq/test`, { method: 'POST' })
        const testData = await testRes.json()
        setTestResult(testData)
      } catch {
        setTestResult({ ok: false, error: 'Test request failed' })
      } finally {
        setTestingConnection(false)
      }
    } catch {
      setError('Could not reach the API.')
    } finally {
      setSavingKey(false)
    }
  }

  const handleRemoveGroqKey = async () => {
    try {
      await fetch(`${getAPI()}/config/groq`, { method: 'DELETE' })
      setGroqConfigured(false)
      setTestResult(null)
    } catch {
      setError('Could not remove key.')
    }
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
        fetch(`${getAPI()}/config/me`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identity: mePath }),
        }),
        fetch(`${getAPI()}/config/groq-settings`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ all_local: allLocal, groq: groqToggles }),
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
      <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
        <DialogHeader className="shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </DialogTitle>
        </DialogHeader>

        <div className="overflow-y-auto flex-1 pr-1">

        {loading && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        {config && !loading && (
          <div className="space-y-6 mt-2">

            {/* AI Provider */}
            <div>
              <p className="text-sm font-medium mb-3">AI Provider</p>

              {/* Subsection A: Groq API Key */}
              <div className="mb-4">
                <label className="text-xs font-medium text-foreground">Groq API key</label>
                <p className="text-xs text-muted-foreground mb-1.5">
                  Store your Groq API key in macOS Keychain for fast AI responses (&lt;20s).
                </p>
                {!groqConfigured ? (
                  <div className="flex gap-2">
                    <Input
                      type="password"
                      value={groqKey}
                      onChange={e => setGroqKey(e.target.value)}
                      placeholder="gsk_…"
                      className="h-8 flex-1 font-mono text-sm"
                    />
                    <Button
                      size="sm"
                      onClick={handleSaveGroqKey}
                      disabled={!groqKey.trim() || savingKey}
                    >
                      {savingKey ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                      Save key
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-xs text-green-500 flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Configured
                    </span>
                    {testingConnection && (
                      <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                    )}
                    {testResult && !testingConnection && (
                      testResult.ok ? (
                        <span className="text-xs text-green-500 flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" />
                          Connected
                        </span>
                      ) : (
                        <span className="text-xs text-destructive flex items-center gap-1">
                          <XCircle className="h-3 w-3" />
                          Invalid key
                        </span>
                      )
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleRemoveGroqKey}
                    >
                      Remove key
                    </Button>
                  </div>
                )}
              </div>

              {/* Subsection B: All-local toggle */}
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-xs font-medium">Local only (Ollama)</p>
                  <p className="text-xs text-muted-foreground">Route all AI features through local Ollama. Disables Groq and Claude.</p>
                </div>
                <Switch
                  checked={allLocal}
                  onCheckedChange={v => { setAllLocal(v); setSaved(false) }}
                />
              </div>

              {/* Subsection C: Groq feature toggles (only when key configured) */}
              {groqConfigured && (
                <div>
                  <p className="text-xs text-muted-foreground mb-2">Groq feature routing</p>
                  <div className={allLocal ? 'opacity-50 pointer-events-none' : ''}>
                    {GROQ_FEATURES.map(f => (
                      <div key={f.key} className="flex items-center justify-between py-2">
                        <div>
                          <p className="text-xs font-medium">{f.label}</p>
                          <p className="text-xs text-muted-foreground">{f.desc}</p>
                        </div>
                        <Switch
                          checked={groqToggles[f.key]}
                          onCheckedChange={v => {
                            setGroqToggles(prev => ({ ...prev, [f.key]: v }))
                            setSaved(false)
                          }}
                          disabled={allLocal}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

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

            {/* Identity */}
            <div>
              <p className="text-sm font-medium mb-3">Identity</p>
              <div>
                <label className="text-xs font-medium text-foreground">You</label>
                <p className="text-xs text-muted-foreground mb-1.5">
                  Select the person that represents you — action items extracted from notes will be assigned to you automatically
                </p>
                <Select value={mePath || '__none__'} onValueChange={v => { setMePath(v === '__none__' ? '' : v); setSaved(false) }}>
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="Not set" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">Not set</SelectItem>
                    {persons.map(p => (
                      <SelectItem key={p.path} value={p.path}>{p.title}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
        </div>
      </DialogContent>
    </Dialog>
  )
}
