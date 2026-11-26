import { useEffect, useId, useRef, useState, type Ref } from 'react'
import { KeyRound, PenLine, ShieldCheck, Sparkles, Upload } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { api, type Backend, type Config } from '@/lib/api'
import { spring } from '@/lib/motion'
import { Callout, Kbd } from './kit'
import { RolePicker } from './RolePicker'

export interface RunSettings {
  name: string; stakeholder_role: string; domain_tag: string; backend: Backend; model: string; ask_clarifying_questions: boolean
}

interface Props {
  config: Config; transcript: string; setTranscript: (t: string) => void
  settings: RunSettings; setSettings: (s: RunSettings) => void
  busy: boolean; onAnalyse: () => void; textareaRef: Ref<HTMLTextAreaElement>
}

const MAX_CHARS = 200_000   // server.AnalysisRequest.transcript max_length
const MAC = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

export function InputPanel({ config, transcript, setTranscript, settings, setSettings, busy, onAnalyse, textareaRef }: Props) {
  const ids = { name: useId(), role: useId(), prefix: useId(), model: useId(), clarify: useId() }
  const file = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const set = (patch: Partial<RunSettings>) => setSettings({ ...settings, ...patch })
  // A hosted backend runs only once its key is in the server's environment (.env).
  const keyEnv = settings.backend === 'gemini' && !config.gemini_key_set ? config.gemini_key_env
    : settings.backend === 'groq' && !config.groq_key_set ? config.groq_key_env : null
  const keyMissing = keyEnv !== null
  // Models the server lists for the picked backend (Groq with its key, Ollama from its pulled models), fetched once per backend.
  const [listed, setListed] = useState<Partial<Record<Backend, { id: string; name: string }[]>>>({})
  useEffect(() => {
    const b = settings.backend
    if ((b === 'groq' || b === 'ollama') && !listed[b]) {
      const load = b === 'groq' ? api.groqModels : api.ollamaModels
      load().then(models => setListed(l => ({ ...l, [b]: models }))).catch(() => setListed(l => ({ ...l, [b]: [] })))
    }
  }, [settings.backend, listed])
  const models = listed[settings.backend]
  const prefixValid = /^[A-Za-z0-9]{1,12}$/.test(settings.domain_tag)
  const words = transcript.trim() ? transcript.trim().split(/\s+/).length : 0
  const canRun = !busy && !keyMissing && prefixValid && !!transcript.trim()

  async function load(f: File | undefined) {
    if (!f) return
    if (!/\.txt$/i.test(f.name) && f.type !== 'text/plain') return toast.error(`${f.name} is not a .txt file. Save the transcript as plain text first.`)
    const text = await f.text()
    if (text.length > MAX_CHARS) return toast.error(`${f.name} is longer than ${MAX_CHARS.toLocaleString()} characters. Split it and analyse each part.`)
    setTranscript(text)
    toast.success(`Loaded ${f.name}.`)
  }

  return (
    <div onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false) }}
         onDrop={e => { e.preventDefault(); setDragging(false); load(e.dataTransfer.files[0]) }}
         className="relative overflow-hidden rounded-2xl bg-card shadow-float has-[textarea:focus-visible]:ring-2 has-[textarea:focus-visible]:ring-primary">
      <div className="flex flex-wrap items-center gap-2 border-b px-5 py-2.5">
        <label htmlFor={ids.name} className="mr-auto flex min-w-0 flex-1 items-center gap-2">
          <PenLine className="size-4 shrink-0 text-primary" aria-hidden />
          <span className="sr-only">Project name</span>
          <input id={ids.name} value={settings.name} maxLength={80} onChange={e => set({ name: e.target.value })}
                 placeholder="Name this project"
                 className="min-w-0 flex-1 rounded-md px-1.5 py-1 text-[15px] font-semibold outline-none placeholder:font-normal placeholder:text-subtle-foreground hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-primary" />
        </label>
        <input ref={file} type="file" accept=".txt,text/plain" className="sr-only" tabIndex={-1} aria-hidden
               onChange={e => { load(e.target.files?.[0]); e.target.value = '' }} />
        <Button variant="outline" size="sm" onClick={() => file.current?.click()}><Upload aria-hidden />Upload .txt</Button>
        <Button variant="secondary" size="sm" onClick={() => {
          setTranscript(config.sample_transcript)
          if (!settings.name.trim()) set({ name: 'Loan origination sample' })
        }}>
          <Sparkles aria-hidden />Load the sample interview
        </Button>
      </div>

      <textarea aria-label="Stakeholder transcript" ref={textareaRef} value={transcript} onChange={e => setTranscript(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && canRun) { e.preventDefault(); onAnalyse() } }}
                placeholder="Paste an interview, meeting notes or a requirements email, or drop a .txt file here."
                className="block min-h-72 w-full resize-y bg-card px-5 py-4 text-[15px] leading-relaxed outline-none placeholder:text-subtle-foreground focus-visible:outline-none" />

      <div className="flex items-center gap-2 border-t bg-muted/50 px-5 py-2 text-xs text-subtle-foreground">
        <ShieldCheck className="size-3.5 shrink-0 text-success" aria-hidden />
        Names, account numbers, cards, PAN, IFSC, phone numbers and emails are masked before any model reads the text.
        <span className="ml-auto shrink-0 tabular-nums">{words.toLocaleString()} words</span>
      </div>

      <div className="grid gap-4 border-t px-5 py-4 md:grid-cols-[1fr_8rem_minmax(0,1.3fr)_auto] md:items-end">
        <div className="grid gap-1.5">
          <Label htmlFor={ids.role} className="text-xs text-muted-foreground">Who was interviewed</Label>
          <RolePicker id={ids.role} label="Who was interviewed" value={settings.stakeholder_role}
                      onChange={v => set({ stakeholder_role: v })} options={config.stakeholder_roles} className="w-full" />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor={ids.prefix} className="text-xs text-muted-foreground">ID prefix</Label>
          <Input id={ids.prefix} value={settings.domain_tag} maxLength={12} aria-invalid={!prefixValid}
                 onChange={e => set({ domain_tag: e.target.value.toUpperCase() })} className="font-mono" />
        </div>
        <div className="grid gap-1.5">
          <span id={`${ids.model}l`} className="text-xs text-muted-foreground">Model</span>
          <div className="flex gap-2">
            <ToggleGroup type="single" value={settings.backend} spacing={0} aria-labelledby={`${ids.model}l`}
                         onValueChange={v => v && set({ backend: v as RunSettings['backend'], model: config.backends[v as RunSettings['backend']] })}
                         className="shrink-0 rounded-lg bg-muted p-0.5">
              {(['ollama', 'gemini', 'groq'] as const).map(b => (
                <ToggleGroupItem key={b} value={b} size="sm"
                                 className="relative rounded-md! px-3 text-muted-foreground hover:bg-transparent data-[state=on]:bg-transparent data-[state=on]:text-foreground">
                  {settings.backend === b && (
                    <motion.span layoutId="backend-thumb" transition={spring.snappy} className="absolute inset-0 rounded-md bg-card shadow-sm ring-1 ring-black/5 dark:ring-white/10" />
                  )}
                  <span className="relative">{{ ollama: 'Local', gemini: 'Gemini', groq: 'Groq' }[b]}</span>
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            {settings.backend === 'groq' || settings.backend === 'ollama' ? (
              <select aria-label={`${settings.backend === 'groq' ? 'Groq' : 'Local'} model`} value={settings.model} onChange={e => set({ model: e.target.value })}
                      className="h-8 w-full min-w-0 rounded-lg border border-input bg-card px-2 font-mono text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30">
                {!models?.some(m => m.id === settings.model) && <option value={settings.model}>{settings.model}</option>}
                {models?.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            ) : (
              <Input aria-label="Model name" value={settings.model} onChange={e => set({ model: e.target.value })}
                     className="min-w-0 font-mono text-xs" />
            )}
          </div>
        </div>
        <Button size="lg" onClick={onAnalyse} disabled={!canRun} className="h-10 gap-2 px-5 text-sm">
          {busy ? 'Analysing…' : 'Analyse transcript'}
          <span className="hidden items-center gap-0.5 opacity-80 sm:flex [&_kbd]:border-white/30 [&_kbd]:bg-white/15 [&_kbd]:text-current [&_kbd]:shadow-none" aria-hidden>
            <Kbd>{MAC ? '⌘' : 'Ctrl'}</Kbd><Kbd>Enter</Kbd>
          </span>
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-t px-5 py-3">
        <div className="flex items-center gap-2.5">
          <Switch id={ids.clarify} aria-labelledby={`${ids.clarify}l`} checked={settings.ask_clarifying_questions}
                  onCheckedChange={c => set({ ask_clarifying_questions: c })} />
          <Label id={`${ids.clarify}l`} htmlFor={ids.clarify} className="font-normal">Suggest follow-up questions for the stakeholder</Label>
        </div>
        <span className="text-xs text-subtle-foreground">
          {settings.backend === 'ollama' ? 'A local model needs about 1 to 3 minutes.' : settings.backend === 'gemini'
            ? 'Gemini’s free tier can take a few minutes.' : 'Groq’s free plan is rate limited (about 30 calls a minute), so a run can take a few minutes.'}
        </span>
      </div>

      <AnimatePresence initial={false}>
        {keyMissing && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                      transition={spring.smooth} className="overflow-hidden">
            <Callout icon={KeyRound} tone="warning" title={`${keyEnv} is not set for the server`} className="mx-5 mb-4">
              Put it in the project’s <code className="font-mono">.env</code> file, then restart <code className="font-mono">python server.py</code>.
              Prism never asks for the key here.
            </Callout>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {dragging && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}
                      className="pointer-events-none absolute inset-2 grid place-items-center rounded-xl border-2 border-dashed border-primary bg-primary-soft/90 text-primary">
            <span className="flex items-center gap-2 font-medium"><Upload className="size-5" aria-hidden />Drop the .txt file to load it</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
