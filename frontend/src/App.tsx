import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { FileText, RotateCcw, ServerCrash } from 'lucide-react'
import { AnimatePresence, MotionConfig, motion, useReducedMotion } from 'motion/react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Toaster } from '@/components/ui/sonner'
import { AuditSheet } from '@/components/AuditSheet'
import { DeliveryStep } from '@/components/DeliveryStep'
import { ExportStep } from '@/components/ExportStep'
import { Spotlight, StartHero } from '@/components/Hero'
import { InputPanel, type RunSettings } from '@/components/InputPanel'
import { EmptyState, IconTile } from '@/components/kit'
import { BRAND } from '@/components/Logo'
import { ProjectsList, ProjectsSheet } from '@/components/ProjectsList'
import { ReviewStep } from '@/components/review/ReviewStep'
import { RunView } from '@/components/RunView'
import { STEPS, StepRail, type Step, type StepInfo } from '@/components/StepRail'
import { TopBar } from '@/components/TopBar'
import { api, roleLabel, type Analysis, type Config, type DecisionRecord, type ProjectSummary } from '@/lib/api'
import { ease, slide } from '@/lib/motion'
import { cn } from '@/lib/utils'

const HeroGradient = lazy(() => import('@/components/HeroGradient'))   // three.js stays out of the first load

const stored = (key: string) => { try { return localStorage.getItem(key) } catch { return null } }
const store = (key: string, value: string | null) => {
  try { if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, value) } catch { /* private mode */ }
}
const ORDER = STEPS.map(s => s.key)
// The settings an analysis ran with, so a retry or re-analysis repeats them.
const runSettings = (a: Analysis, c: Config): RunSettings => ({
  ...a.settings, model: a.settings.model || c.backends[a.settings.backend],
})

const initialStep = (): Step => {
  const s = new URLSearchParams(location.search).get('step') as Step | null
  return s && ORDER.includes(s) && s !== 'transcript' ? s : 'review'
}

export default function App() {
  const [config, setConfig] = useState<Config>()
  const [settings, setSettings] = useState<RunSettings>()
  const [transcript, setTranscript] = useState('')
  const [reviewer, setReviewer] = useState(stored('finreq.reviewer') ?? 'business_analyst')
  const [analysis, setAnalysis] = useState<Analysis>()
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [projectsOpen, setProjectsOpen] = useState(false)
  // ?analysis=<id> (a link) or the last run in this browser. While it loads we show the
  // loading screen, not the start screen: rendering the hero first and then cross-fading
  // to the review was a visible flash on every reload.
  const [restoreId] = useState(() => new URLSearchParams(location.search).get('analysis') ?? stored('finreq.analysis'))
  const [composing, setComposing] = useState(!restoreId)
  const [step, setStep] = useState<Step>(initialStep)
  const [dir, setDir] = useState(1)
  const [auditOpen, setAuditOpen] = useState(false)
  const [decisions, setDecisions] = useState<DecisionRecord[]>([])
  const [loadError, setLoadError] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composerRef = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()
  const [gradient, setGradient] = useState(false)

  useEffect(() => {
    api.config().then(c => {
      setConfig(c)
      setSettings({ name: '', stakeholder_role: 'loan_officer', domain_tag: 'LOAN', backend: c.default_backend,
                    model: c.backends[c.default_backend], ask_clarifying_questions: true })
    }).catch(() => setLoadError(true))
    if (restoreId) api.get(restoreId).then(a => {
      setAnalysis(a)
      if (a.transcript !== undefined) setTranscript(a.transcript)
    }).catch(() => {
      store('finreq.analysis', null)
      setComposing(true)
      toast.error('That analysis is gone: the server was restarted. Start a new one.', { id: 'gone' })
    })
  }, [restoreId])   // restoreId never changes: this runs once

  // The project list is fresh whenever it is on screen: the start page or the Projects sheet.
  useEffect(() => { if (composing || projectsOpen) api.projects().then(setProjects).catch(() => {}) }, [composing, projectsOpen])

  // three.js parses and compiles shaders on the main thread; doing that while the intro
  // animates made the first second stutter. The CSS gradient shows until then.
  useEffect(() => {
    const timer = setTimeout(() => setGradient(true), 900)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => store('finreq.reviewer', reviewer), [reviewer])

  // Poll while the pipeline runs. Three misses in a row: say so, once.
  useEffect(() => {
    if (analysis?.status !== 'running') return
    let misses = 0
    const timer = setInterval(() => api.get(analysis.id).then(a => { misses = 0; setAnalysis(a) }).catch(() => {
      if (++misses === 3) toast.error('Lost contact with the server. Retrying.', { id: 'poll' })
    }), 1000)
    return () => clearInterval(timer)
  }, [analysis?.id, analysis?.status])

  // This analysis's decisions, for the inspector's history; refreshed after every change.
  useEffect(() => {
    if (analysis?.status !== 'done') return
    api.audit(analysis.id).then(d => setDecisions(d.decisions)).catch(() => {})
  }, [analysis])

  // ?analysis=&step= follow you, so a reload or a shared link lands on the same step.
  useEffect(() => {
    const url = new URL(location.href)
    if (analysis && !composing) { url.searchParams.set('analysis', analysis.id); url.searchParams.set('step', step) }
    else { url.searchParams.delete('analysis'); url.searchParams.delete('step') }
    history.replaceState(null, '', url)
  }, [analysis?.id, composing, step])  // eslint-disable-line react-hooks/exhaustive-deps

  function go(next: Step) {
    const from = composing ? 'transcript' : step
    setDir(ORDER.indexOf(next) >= ORDER.indexOf(from) ? 1 : -1)
    if (next === 'transcript') setComposing(true)
    else { setStep(next); setComposing(false) }
    window.scrollTo({ top: 0 })   // instant: the new step already slides in; two motions at once read as a lurch
  }

  function show(a: Analysis) {
    store('finreq.analysis', a.id)
    setAnalysis(a)
    if (a.transcript !== undefined) setTranscript(a.transcript)   // a running analysis does not send it
    setStep('review')
    setDir(1)
    setComposing(false)
    window.scrollTo({ top: 0 })
  }

  async function open(id: string) {
    setProjectsOpen(false)
    try { show(await api.get(id)) } catch (e) { toast.error((e as Error).message) }
  }

  // Deleting the open project lands on a clean start screen.
  async function remove(p: ProjectSummary) {
    try {
      await api.remove(p.id)
      setProjects(ps => ps.filter(x => x.id !== p.id))
      if (analysis?.id === p.id) {
        store('finreq.analysis', null)
        setAnalysis(undefined)
        setComposing(true)
      }
      toast.success(`Deleted “${p.name}”. Its decisions stay in the audit trail.`)
    } catch (e) { toast.error((e as Error).message) }
  }

  // "New analysis" from the Projects sheet: a clean composer, not the open project's text.
  function startNew() {
    setProjectsOpen(false)
    setTranscript('')
    if (settings) setSettings({ ...settings, name: '' })
    go('transcript')
    focusComposer()
  }

  async function analyse(text = transcript, s = settings) {
    if (!s) return
    try {
      const { id } = await api.start({ ...s, transcript: text, model: s.model || null })
      setTranscript(text)
      show(await api.get(id))
    } catch (e) { toast.error((e as Error).message) }
  }

  function reanalyse(answers: Record<string, string>) {
    const base = analysis?.transcript ?? transcript
    if (!base.trim()) {
      toast.error('The original transcript is not loaded in this tab. Paste it on the Transcript step, then answer again.')
      return
    }
    const qa = Object.entries(answers).filter(([, a]) => a.trim()).map(([q, a]) => `Q: ${q}\nA: ${a}`)
    const text = `${base}\n\nAdditional clarifications:\n${qa.join('\n')}`
    analyse(text, analysis && config ? runSettings(analysis, config) : settings)
  }

  function retry() {
    if (analysis && config) analyse(analysis.transcript ?? transcript, runSettings(analysis, config))
    else analyse()
  }

  function focusComposer() {
    composerRef.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' })
    setTimeout(() => textareaRef.current?.focus({ preventScroll: true }), reduce ? 0 : 450)
  }

  if (loadError) return (
    <div className="grid min-h-svh place-items-center bg-background p-6">
      <EmptyState icon={ServerCrash} title={`${BRAND} cannot reach its server`}
                  action={<Button onClick={() => location.reload()}><RotateCcw aria-hidden />Reload</Button>}>
        Start it with <code className="font-mono">python server.py</code>, then reload this page.
      </EmptyState>
    </div>
  )
  if (!config || !settings || (!composing && !analysis)) return (
    <main aria-busy className="min-h-svh bg-ink bg-[radial-gradient(120%_120%_at_10%_0%,var(--brand)_0%,var(--ink)_55%)] px-4 pt-[26rem] md:px-8">
      <h1 className="sr-only">Loading {BRAND}</h1>
      <Skeleton className="mx-auto h-96 max-w-7xl rounded-2xl bg-white/10" />
    </main>
  )

  const status = analysis?.status
  const view = composing || !analysis ? 'start' : status === 'running' ? 'run' : status === 'failed' ? 'failed' : 'steps'
  const reqs = analysis?.requirements ?? []
  const decided = reqs.filter(r => r.approval_status === 'approved' || r.approval_status === 'rejected').length
  const sdlc = analysis?.sdlc
  const ran = status === 'done'
  const later = 'After the analysis'
  const info: Record<Step, StepInfo> = {
    transcript: { done: ran, hint: !analysis ? 'Paste or load' : status === 'running' ? 'Analysing…' : status === 'failed' ? 'Stopped'
      : `${roleLabel(analysis.settings.stakeholder_role)}, ${Math.round(analysis.elapsed)}s` },
    review: { done: ran && reqs.length > 0 && decided === reqs.length, disabled: !ran, hint: ran ? `${decided} of ${reqs.length} decided` : later },
    delivery: { done: !!sdlc?.baselined, disabled: !ran, hint: sdlc ? `${sdlc.signed.length} of ${sdlc.approvers.length} signed` : later },
    export: { done: false, disabled: !ran, hint: !ran ? later : !sdlc?.baselined ? 'Waiting on sign-off'
      : decided < reqs.length ? `${reqs.length - decided} still open` : 'Ready' },
  }
  const hero = view !== 'steps'

  return (
    <MotionConfig reducedMotion="user">
      <div className="flex min-h-svh flex-col">
        {/* The brand backdrop fills the window behind the start, run and failed views, and
            the content scrolls over it. Fixed, so the WebGL canvas is only ever
            viewport-sized and never leaves the screen. */}
        <AnimatePresence initial={false}>
          {hero && (
            <motion.div key="backdrop" aria-hidden className="fixed inset-0 -z-10 bg-ink"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.35, ease }}>
              <div className="absolute inset-0 bg-[radial-gradient(120%_120%_at_10%_0%,var(--brand)_0%,var(--ink)_55%)]" />
              {gradient && <Suspense fallback={null}><HeroGradient /></Suspense>}
              <div className="absolute inset-0 bg-gradient-to-r from-ink/70 via-ink/35 to-ink/60" />
              {view === 'start' && <Spotlight />}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Transparent over the backdrop; a sticky ink bar on the steps. */}
        <header className={cn('isolate text-ink-foreground', hero ? 'relative' : 'sticky top-0 z-30 bg-ink shadow-[0_1px_0_rgb(255_255_255/0.08)]')}>
          {!hero && <div aria-hidden className="absolute inset-0 -z-10 bg-[radial-gradient(120%_120%_at_10%_0%,var(--brand)_0%,var(--ink)_55%)]" />}
          <TopBar variant={hero ? 'hero' : 'bar'} onHome={() => go('transcript')} onProjects={() => setProjectsOpen(true)} reviewer={reviewer} setReviewer={setReviewer}
                  roles={config.reviewer_roles} onAudit={ran ? () => setAuditOpen(true) : undefined}
                  rail={analysis && <StepRail active={view === 'steps' ? step : 'transcript'} info={info} onSelect={go} />} />
        </header>

        <main className="flex flex-1 flex-col">
          {/* One view at a time: the old one fades out, then the new one fades in. */}
          <AnimatePresence mode="wait" initial={false}>
            {view === 'start' && (
              <motion.div key="start" className="text-ink-foreground" exit={{ opacity: 0, transition: { duration: 0.18, ease } }}>
                <StartHero onTrySample={() => { setTranscript(config.sample_transcript); focusComposer() }} onPasteOwn={focusComposer} />
                <motion.div ref={composerRef} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease, delay: 0.3 }}
                            className="mx-auto w-full max-w-7xl scroll-mt-24 px-4 pb-24 text-foreground md:px-8">
                  <InputPanel config={config} transcript={transcript} setTranscript={setTranscript} settings={settings} textareaRef={textareaRef}
                              setSettings={setSettings} busy={status === 'running'} onAnalyse={() => analyse()} />
                  <ProjectsList projects={projects} onOpen={open} onDelete={remove} onShowAll={() => setProjectsOpen(true)} />
                </motion.div>
              </motion.div>
            )}

            {view === 'run' && analysis && (
              <motion.div key="run" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25, ease }}>
                <RunView stages={analysis.stages} elapsed={analysis.elapsed} model={analysis.settings.model || settings.model}
                         backend={analysis.settings.backend} askQuestions={analysis.settings.ask_clarifying_questions}
                         stakeholder={analysis.settings.stakeholder_role} />
              </motion.div>
            )}

            {view === 'failed' && analysis && (
              <motion.section key="failed" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3, ease }}
                              className="mx-auto w-full max-w-3xl px-4 pt-16 md:px-8">
                <div className="flex gap-4 rounded-2xl bg-card p-6 shadow-float ring-1 ring-danger-border">
                  <IconTile icon={ServerCrash} tone="danger" />
                  <div className="min-w-0">
                    <h1 className="text-lg font-semibold text-danger">The analysis stopped</h1>
                    <p className="mt-2 whitespace-pre-line text-muted-foreground">{analysis.error}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {(analysis.transcript ?? transcript).trim() && <Button onClick={retry}><RotateCcw aria-hidden />Try again</Button>}
                      <Button variant="outline" onClick={() => go('transcript')}><FileText aria-hidden />Change the settings</Button>
                    </div>
                  </div>
                </div>
              </motion.section>
            )}

            {view === 'steps' && analysis && (
              <motion.div key="steps" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3, ease }}
                          className="relative mx-auto w-full max-w-7xl flex-1 px-4 pt-6 pb-20 md:px-8 md:pt-8">
                <AnimatePresence mode="popLayout" custom={dir} initial={false}>
                  <motion.div key={step} custom={dir} variants={slide} initial="enter" animate="center" exit="exit">
                    {step === 'review' && (
                      <ReviewStep analysis={analysis} reviewer={reviewer} decisions={decisions} onChange={setAnalysis}
                                  onNext={() => go('delivery')} onReanalyse={reanalyse} onTranscript={() => go('transcript')} />
                    )}
                    {step === 'delivery' && (
                      <DeliveryStep analysis={analysis} reviewer={reviewer} setReviewer={setReviewer} onChange={setAnalysis} onNext={() => go('export')} />
                    )}
                    {step === 'export' && <ExportStep analysis={analysis} />}
                  </motion.div>
                </AnimatePresence>
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        <ProjectsSheet open={projectsOpen} onOpenChange={setProjectsOpen} projects={projects} onOpen={open} onDelete={remove} onNew={startNew}
                       currentId={!composing ? analysis?.id : undefined} />
        {analysis && ran && <AuditSheet open={auditOpen} onOpenChange={setAuditOpen} analysisId={analysis.id} refreshKey={analysis} />}
        <Toaster position="bottom-right" />
      </div>
    </MotionConfig>
  )
}
