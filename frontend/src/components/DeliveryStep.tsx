import { useEffect, useState } from 'react'
import {
  BarChart3, Check, ChevronDown, CircleAlert, CircleCheck, Download, FileText, Repeat, ShieldCheck, SlidersHorizontal,
  Sparkles, Users, Workflow,
} from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Slider } from '@/components/ui/slider'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { api, roleLabel, type Analysis } from '@/lib/api'
import { ease, spring } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { CheckStamp, NextStep, PANEL, PanelHeader, ProgressRing } from './kit'
import { Pill } from './pills'

const TOP = 5
const initials = (role: string) => role.split('_').map(w => w[0]!.toUpperCase()).join('').slice(0, 2)

interface Props { analysis: Analysis; reviewer: string; setReviewer: (r: string) => void; onChange: (a: Analysis) => void; onNext: () => void }

export function DeliveryStep({ analysis, reviewer, setReviewer, onChange, onNext }: Props) {
  const sdlc = analysis.sdlc!
  const [factors, setFactors] = useState(sdlc.factors)
  useEffect(() => setFactors(sdlc.factors), [sdlc.factors])
  const [showAll, setShowAll] = useState(false)
  const chosen = sdlc.ranking.find(s => s.key === sdlc.chosen)!
  const chosenRank = sdlc.ranking.indexOf(chosen)
  const visible = showAll ? sdlc.ranking : sdlc.ranking.filter((s, i) => i < TOP || s.key === sdlc.chosen)
  const canSign = sdlc.approvers.includes(reviewer) && !sdlc.signed.includes(reviewer)

  async function update(body: { factors?: Record<string, number>; chosen?: string }) {
    try { onChange(await api.sdlc(analysis.id, body)) } catch (e) { toast.error((e as Error).message) }
  }

  async function signOff() {
    try {
      onChange(await api.signoff(analysis.id, reviewer))
      toast.success(`Signed off ${chosen.name} as ${roleLabel(reviewer).toLowerCase()}.`)
    } catch (e) { toast.error((e as Error).message) }
  }

  return (
    <div className="grid gap-5">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">Choose the delivery model</h1>
          <p className="mt-0.5 max-w-[72ch] text-muted-foreground">
            Ten models ranked by fit to this project. Pick one to see its workflow; the four approvers then sign off that choice.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ProgressRing value={sdlc.signed.length / sdlc.approvers.length} size={52} tone={sdlc.baselined ? 'success' : 'primary'}
                        label={`${sdlc.signed.length} of ${sdlc.approvers.length} sign-offs`}>
            {sdlc.signed.length}/{sdlc.approvers.length}
          </ProgressRing>
          <div className="leading-tight">
            <p className="font-medium">{sdlc.baselined ? 'Baselined' : 'Sign-offs'}</p>
            <p className="text-subtle-foreground">{chosen.name}</p>
          </div>
        </div>
      </header>

      <div className="grid items-start gap-5 md:grid-cols-[minmax(0,1fr)_18rem] lg:grid-cols-[minmax(0,1fr)_21rem]">
        <div className="grid min-w-0 content-start gap-5">
          <section className={cn(PANEL, 'p-5')}>
            <PanelHeader icon={BarChart3} title="Ranking">Weighted fit across 13 factors. Choose a row to make it the plan.</PanelHeader>
            <motion.ul layout className="mt-4 grid gap-1">
              <AnimatePresence initial={false}>
                {visible.map(s => {
                  const rank = sdlc.ranking.indexOf(s) + 1
                  const isChosen = s.key === sdlc.chosen
                  return (
                    <motion.li key={s.key} layout transition={spring.smooth}
                               initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                      <button type="button" onClick={() => update({ chosen: s.key })} aria-pressed={isChosen}
                              className={cn('grid w-full grid-cols-[1.5rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-muted/70',
                                isChosen && 'bg-primary-soft ring-1 ring-primary/25 ring-inset hover:bg-primary-soft')}>
                        <span className={cn('row-span-2 grid size-6 place-items-center rounded-full text-xs font-semibold tabular-nums',
                          isChosen ? 'bg-primary text-primary-foreground' : 'bg-muted text-subtle-foreground')}>
                          {isChosen ? <Check className="size-3.5" strokeWidth={3} aria-hidden /> : rank}
                        </span>
                        <span className="flex min-w-0 flex-wrap items-center gap-2">
                          <span className={cn('truncate', isChosen && 'font-semibold')}>{s.name}</span>
                          {s.key === sdlc.recommended && <Pill tone="primary" icon={Sparkles}>Recommended</Pill>}
                        </span>
                        <span className="tabular-nums text-muted-foreground">{s.score.toFixed(1)}%</span>
                        <span className="col-span-2 h-1.5 overflow-hidden rounded-full bg-muted">
                          <motion.span className={cn('block h-full origin-left rounded-full', isChosen ? 'bg-primary' : 'bg-border-strong')}
                                       initial={{ scaleX: 0 }} animate={{ scaleX: s.score / 100 }} transition={spring.gentle} />
                        </span>
                      </button>
                    </motion.li>
                  )
                })}
              </AnimatePresence>
            </motion.ul>
            <Button variant="ghost" size="sm" className="mt-2" onClick={() => setShowAll(!showAll)} aria-expanded={showAll}>
              <ChevronDown className={cn('transition-transform', showAll && 'rotate-180')} aria-hidden />
              {showAll ? `Show the top ${TOP}` : `Show all ${sdlc.ranking.length} models`}
            </Button>
          </section>

          <section className={cn(PANEL, 'p-5')}>
            <PanelHeader icon={ShieldCheck} title={`Why ${chosen.name}`}>
              {chosenRank === 0 ? 'The top fit for this project.' : `Ranked ${chosenRank + 1} of ${sdlc.ranking.length}; a reviewer chose it over ${sdlc.ranking[0].name}.`}
            </PanelHeader>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Reasons title="In favour" icon={CircleCheck} tone="text-success" items={chosen.supports} empty="Nothing strongly in favour." />
              <Reasons title="Against" icon={CircleAlert} tone="text-warning" items={chosen.against} empty="Nothing strongly against." />
            </div>
          </section>

          <section className={cn(PANEL, 'p-5')}>
            <PanelHeader icon={Workflow} title={`${chosen.name} workflow`}>Financial controls are built into the phases, not added at the end.</PanelHeader>
            <Timeline key={chosen.key} phases={sdlc.workflow} />
          </section>
        </div>

        <aside className="grid content-start gap-5 md:sticky md:top-32 lg:top-20">
          <section className={cn(PANEL, 'p-5')}>
            <h2 className="text-base font-semibold">Sign-off</h2>
            <p className="mt-0.5 text-muted-foreground">All four approvers sign the same model before it is baselined.</p>
            <ul className="mt-4 grid gap-2.5">
              {sdlc.approvers.map(role => {
                const signed = sdlc.signed.includes(role)
                return (
                  <li key={role} className="flex items-center gap-3">
                    <motion.span key={String(signed)} initial={signed ? { scale: 0.6 } : false} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 500, damping: 15 }}
                                 className={cn('grid size-8 shrink-0 place-items-center rounded-full text-xs font-semibold',
                                   signed ? 'bg-success-soft text-success ring-2 ring-success/40' : 'bg-muted text-subtle-foreground')}>
                      {signed ? <Check className="size-4" strokeWidth={3} aria-hidden /> : initials(role)}
                    </motion.span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate">{roleLabel(role)}</span>
                      <span className={cn('text-xs', signed ? 'text-success' : 'text-subtle-foreground')}>{signed ? 'Signed' : role === reviewer ? 'You, waiting' : 'Waiting'}</span>
                    </span>
                    {!signed && role !== reviewer && (
                      <Button variant="ghost" size="sm" onClick={() => setReviewer(role)}>Switch to</Button>
                    )}
                  </li>
                )
              })}
            </ul>
            <AnimatePresence mode="wait" initial={false}>
              {sdlc.baselined ? (
                <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-5 grid justify-items-center gap-2 rounded-xl bg-success-soft px-4 py-5 text-center">
                  <CheckStamp size={56} />
                  <p className="font-medium text-success">{chosen.name} is baselined</p>
                </motion.div>
              ) : canSign ? (
                <motion.div key="sign" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <Button className="mt-5 w-full" size="lg" onClick={signOff}>Sign off as {roleLabel(reviewer).toLowerCase()}</Button>
                </motion.div>
              ) : (
                <motion.p key="hint" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="mt-5 text-subtle-foreground">
                  {sdlc.approvers.includes(reviewer) ? 'You have signed. ' : `A ${roleLabel(reviewer).toLowerCase()} cannot sign. `}
                  Use “Switch to” to sign as another approver.
                </motion.p>
              )}
            </AnimatePresence>
          </section>

          <Collapsible className={cn(PANEL, 'p-5')}>
            <CollapsibleTrigger className="group flex w-full items-start gap-3 text-left">
              <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground"><SlidersHorizontal className="size-4" aria-hidden /></span>
              <span className="flex-1">
                <span className="block font-semibold">Adjust project profile</span>
                <span className="text-muted-foreground">13 factors; {sdlc.derived.length} come from the requirements.</span>
              </span>
              <ChevronDown className="mt-1 size-4 text-subtle-foreground transition-transform group-data-[state=open]:rotate-180" aria-hidden />
            </CollapsibleTrigger>
            <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
              <div className="mt-5 grid gap-4">
                {Object.entries(sdlc.labels).map(([key, label]) => (
                  <div key={key} className="grid gap-2">
                    <div className="flex items-start justify-between gap-3">
                      <span id={`f-${key}`} className="leading-snug">
                        {label}
                        {sdlc.derived.includes(key) && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span tabIndex={0} className="ml-1.5 inline-flex cursor-help align-middle"><Pill icon={FileText}>From requirements</Pill></span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-56 text-pretty">Derived from the analysed requirements. You can still override it.</TooltipContent>
                          </Tooltip>
                        )}
                      </span>
                      <span className="tabular-nums text-muted-foreground">{(factors[key] ?? 0).toFixed(2)}</span>
                    </div>
                    <Slider aria-labelledby={`f-${key}`} min={0} max={1} step={0.05} value={[factors[key] ?? 0]}
                            onValueChange={([v]) => setFactors({ ...factors, [key]: v })}
                            onValueCommit={([v]) => update({ factors: { [key]: v } })} />
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        </aside>
      </div>

      <NextStep ready={sdlc.baselined} icon={Download} label="Continue to export" onClick={onNext}
                hint={sdlc.baselined ? `${chosen.name} is baselined for this project.` : `${sdlc.approvers.length - sdlc.signed.length} sign-offs still needed. You can export before then.`} />
    </div>
  )
}

function Reasons({ title, icon: Icon, tone, items, empty }: { title: string; icon: typeof Check; tone: string; items: string[]; empty: string }) {
  return (
    <div>
      <h3 className="mb-2 font-medium">{title}</h3>
      {items.length ? (
        <ul className="grid gap-1.5">
          {items.map(s => <li key={s} className="flex gap-2 text-muted-foreground"><Icon className={cn('mt-0.5 size-4 shrink-0', tone)} aria-hidden />{s}</li>)}
        </ul>
      ) : <p className="text-subtle-foreground">{empty}</p>}
    </div>
  )
}

// The chosen model's phases. A real sequence, so the markers are numbered.
function Timeline({ phases }: { phases: NonNullable<Analysis['sdlc']>['workflow'] }) {
  return (
    <div className="relative mt-5">
      <motion.span aria-hidden className="absolute top-3 bottom-3 left-4 w-px origin-top bg-border-strong"
                   initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ duration: 0.6, ease }} />
      <ol className="relative grid">
        {phases.map((p, i) => (
          <motion.li key={p.name} className="relative grid grid-cols-[2rem_minmax(0,1fr)] gap-3 pb-6 last:pb-0"
                     initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ ...spring.smooth, delay: 0.07 * i }}>
            <span className="relative z-10 grid size-8 place-items-center rounded-full bg-card text-sm font-semibold tabular-nums ring-1 ring-border-strong">{i + 1}</span>
            <div className="grid gap-2 pt-1">
              <p className="flex flex-wrap items-center gap-2 font-medium">{p.name}{p.repeats && <Pill tone="primary" icon={Repeat}>Repeats each iteration</Pill>}</p>
              <ul className="flex flex-wrap gap-1.5">
                {p.activities.map(a => <li key={a} className="rounded-md bg-muted px-2 py-1 text-[13px] text-muted-foreground">{a}</li>)}
              </ul>
              <p className="flex gap-2 text-subtle-foreground"><Users className="mt-0.5 size-4 shrink-0" aria-hidden />{p.roles.join(', ')}</p>
              <p className="flex gap-2 text-subtle-foreground"><FileText className="mt-0.5 size-4 shrink-0" aria-hidden />Delivers {p.deliverables.join(', ').toLowerCase()}</p>
              <p className="flex gap-2 rounded-lg bg-warning-soft/60 px-2.5 py-1.5 text-foreground ring-1 ring-warning-border/60 ring-inset">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden /><span><span className="text-muted-foreground">Exit gate:</span> {p.exit_gate}</span>
              </p>
            </div>
          </motion.li>
        ))}
      </ol>
    </div>
  )
}
