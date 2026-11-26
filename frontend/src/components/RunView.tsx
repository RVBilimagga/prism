import { Check } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { ThinkingOrb } from 'thinking-orbs'
import { roleLabel } from '@/lib/api'
import { spring } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { CountUp, ProgressBar } from './kit'

// The pipeline's stages in order (src/finreq/pipeline.py announces them). Stages
// that have started show the server's own label; the rest come from here by position.
export const PLANNED_STAGES = [
  'Masking sensitive data', 'Checking for missing or vague information', 'Extracting requirements',
  'Classifying requirements', 'Running quality checks', 'Checking for duplicates and conflicts',
  'Mapping requirements to policies and regulations', 'Reviewing security and privacy coverage', 'Assessing risk',
  'Validating and routing for approval', 'Restoring masked values and saving',
]

type OrbState = 'working' | 'searching' | 'solving' | 'composing' | 'weaving'

// Which orb animation best describes what each pipeline stage is doing.
function orbFor(stage: string): OrbState {
  if (/policies|regulations/i.test(stage)) return 'searching'   // knowledge-base retrieval
  if (/extracting/i.test(stage)) return 'composing'             // writing requirement records
  if (/duplicates|conflicts/i.test(stage)) return 'weaving'     // comparing requirements with each other
  if (/classifying|clarif|vague|risk|security/i.test(stage)) return 'solving'
  return 'working'
}

const trim = (s: string) => s.replace(/\.\.\.$/, '')

interface Props { stages: string[]; elapsed: number; model: string; backend: string; askQuestions: boolean; stakeholder: string }

// Rendered on the ink hero while the pipeline runs.
export function RunView({ stages, elapsed, model, backend, askQuestions, stakeholder }: Props) {
  const plan = askQuestions ? PLANNED_STAGES : PLANNED_STAGES.filter((_, i) => i !== 1)
  const active = stages.at(-1)
  const rows = plan.map((planned, i) => ({
    label: i < stages.length ? trim(stages[i]) : planned,
    state: i < stages.length - 1 ? 'done' : i === stages.length - 1 ? 'active' : 'pending',
  }))

  return (
    <section aria-live="polite" aria-busy className="mx-auto grid w-full max-w-7xl items-start gap-10 px-4 pb-20 pt-8 text-ink-foreground md:px-8 md:pt-14 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <div className="lg:pt-6">
        <div className="flex items-center gap-5">
          {/* Light: white tile, dark dots. Dark: a translucent tile that takes the backdrop's blue, white dots
              (the orb's auto theme follows .dark). */}
          <div className="grid size-20 shrink-0 place-items-center rounded-2xl bg-white/95 shadow-float dark:bg-white/10 dark:shadow-none dark:ring-1 dark:ring-white/20">
            <ThinkingOrb state={active ? orbFor(active) : 'working'} size={64} aria-label={active ? trim(active) : 'Starting analysis'} />
          </div>
          <div className="min-w-0">
            <p className="text-ink-muted">Analysing a {roleLabel(stakeholder).toLowerCase()} interview</p>
            <AnimatePresence mode="wait" initial={false}>
              <motion.h1 key={active ?? 'start'} initial={{ opacity: 0, y: 8, filter: 'blur(6px)' }}
                         animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} exit={{ opacity: 0, y: -8, filter: 'blur(6px)' }}
                         transition={{ duration: 0.25 }} className="text-2xl font-semibold tracking-tight md:text-3xl">
                {active ? trim(active) : 'Starting analysis'}
              </motion.h1>
            </AnimatePresence>
          </div>
        </div>

        <ProgressBar tone="signal" value={Math.min(stages.length / plan.length, 0.97)} label="Pipeline progress"
                     className="mt-10 h-1" trackClassName="bg-white/15" />
        <div className="mt-3 flex flex-wrap justify-between gap-2 text-ink-muted">
          <span>Running on <span className="font-mono text-ink-foreground">{model}</span></span>
          <span><CountUp value={Math.round(elapsed)} className="text-ink-foreground" />s so far</span>
        </div>
        <p className="mt-6 max-w-md text-ink-muted">
          {backend === 'gemini' ? 'Gemini’s free tier waits out rate limits, so a run can take a few minutes.'
            : backend === 'groq' ? 'Groq’s free plan waits out rate limits, so a run can take a few minutes.'
            : 'A local model usually needs 1 to 3 minutes. You can leave this tab; the run keeps going.'}
        </p>
      </div>

      {/* A white panel in light mode, like the orb tile; ink glass in dark. */}
      <ol className="grid gap-0.5 rounded-2xl bg-card/95 p-2 shadow-float dark:bg-ink/70 dark:shadow-none dark:ring-1 dark:ring-white/10" aria-label="Pipeline stages">
        {rows.map(({ label, state }, i) => (
          <li key={i} className={cn('flex items-center gap-3 rounded-xl px-3 py-2 transition-colors', state === 'active' && 'bg-primary-soft dark:bg-white/[0.07]')}>
            <span className="relative grid size-5 shrink-0 place-items-center">
              {state === 'done' && (
                <motion.span initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={spring.snappy}
                             className="grid size-5 place-items-center rounded-full bg-primary-soft text-primary dark:bg-signal/20 dark:text-signal">
                  <Check className="size-3" strokeWidth={3} aria-hidden />
                </motion.span>
              )}
              {state === 'active' && (
                <>
                  <span className="absolute size-4 animate-ping rounded-full bg-signal/50" />
                  <span className="size-2.5 rounded-full bg-signal" />
                </>
              )}
              {state === 'pending' && <span className="size-2.5 rounded-full ring-1 ring-subtle-foreground/60 dark:ring-ink-muted/70" />}
            </span>
            <span className={cn(state === 'active' ? 'shimmer font-medium text-foreground dark:text-ink-foreground'
              : state === 'done' ? 'text-foreground dark:text-ink-muted' : 'text-muted-foreground dark:text-ink-muted')}>
              {label}
              <span className="sr-only">{state === 'done' ? ', done' : state === 'active' ? ', running' : ', waiting'}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}
