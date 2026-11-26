import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { CheckCheck, FileText, Grid3x3, Inbox, List, MessagesSquare, Workflow } from 'lucide-react'
import { motion } from 'motion/react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { api, roleLabel, type Analysis, type Decision, type DecisionRecord, type Requirement } from '@/lib/api'
import { spring } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { CheckStamp, CountUp, Donut, EmptyState, Kbd, NextStep, PANEL } from '../kit'
import { STATUS } from '../pills'
import { Inspector, VERB } from './Inspector'
import { QuestionsSheet } from './QuestionsSheet'
import { FILTERS, openIssues, RequirementList, type Filter, type Flash } from './RequirementList'
import { cellOf, RISK_ORDER, RiskMap } from './RiskMap'

const desktopQuery = '(min-width: 768px)'   // a desktop app: side-by-side from tablet width up
const useDesktop = () => useSyncExternalStore(
  cb => { const m = matchMedia(desktopQuery); m.addEventListener('change', cb); return () => m.removeEventListener('change', cb) },
  () => matchMedia(desktopQuery).matches)

interface Props {
  analysis: Analysis; reviewer: string; decisions: DecisionRecord[]
  onChange: (a: Analysis) => void; onNext: () => void
  onReanalyse: (answers: Record<string, string>) => void; onTranscript: () => void
}

export function ReviewStep({ analysis, reviewer, decisions, onChange, onNext, onReanalyse, onTranscript }: Props) {
  const reqs = useMemo(() => analysis.requirements ?? [], [analysis.requirements])
  const risks = useMemo(() => analysis.risks ?? [], [analysis.risks])
  const questions = analysis.questions ?? []
  const stakeholder = roleLabel(analysis.settings.stakeholder_role)
  const counts = useMemo(() => Object.fromEntries(FILTERS.map(f => [f, f === 'all' ? reqs.length
    : reqs.filter(r => r.approval_status === f).length])), [reqs]) as Record<Filter, number>
  const [filter, setFilter] = useState<Filter>(counts.pending_review ? 'pending_review' : 'all')
  const [view, setView] = useState<'list' | 'risk'>('list')
  const [cell, setCell] = useState<string | null>(null)
  // The rows the keys and auto-advance walk: the list's filter, or the risk map's register.
  const shown = useMemo(() => {
    const rows = view === 'list'
      ? reqs.filter(r => filter === 'all' || r.approval_status === filter)
      : risks.filter(k => !cell || cellOf(k) === cell)
          .map(k => reqs.find(r => r.id === k.related_requirement_id)).filter((r): r is Requirement => !!r)
    return rows.sort((a, b) => RISK_ORDER[a.risk_level] - RISK_ORDER[b.risk_level] || a.id.localeCompare(b.id))
  }, [reqs, risks, filter, view, cell])
  const [selectedId, setSelectedId] = useState<string | undefined>(shown[0]?.id)
  const selected = shown.find(r => r.id === selectedId) ?? shown[0]
  const [busy, setBusy] = useState(false)
  const [flash, setFlash] = useState<Flash | null>(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [note, setNote] = useState('')
  const [sheetOpen, setSheetOpen] = useState(false)
  const [questionsOpen, setQuestionsOpen] = useState(false)
  const desktop = useDesktop()

  const decided = counts.approved + counts.rejected
  const allDecided = reqs.length > 0 && decided === reqs.length
  const bulkCount = reqs.filter(r => r.approval_status === 'pending_review' && !openIssues(r)).length

  useEffect(() => { setEditing(false); setNote('') }, [selected?.id])

  async function decide(action: Decision) {
    if (!selected || busy) return
    const index = shown.findIndex(r => r.id === selected.id)
    const next = shown[index + 1] ?? shown[index - 1]
    setBusy(true)
    try {
      // The row flashes its outcome while the request runs; a keyboard decision never waits on animation.
      if (action === 'accept' || action === 'reject') setFlash({ id: selected.id, tone: action === 'accept' ? 'success' : 'danger' })
      const updated = await api.decide(analysis.id, selected.id, {
        action, actor_role: reviewer, note, statement: action === 'modify' ? draft : undefined,
      })
      onChange(updated)
      if (action === 'modify') setEditing(false)
      else {
        if (next) setSelectedId(next.id)
        else setSheetOpen(false)
      }
      toast.success(`${selected.id} ${action === 'modify' ? 'edited and sent back for review' : VERB[action]}.`)
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setBusy(false)
      setFlash(null)
    }
  }

  async function bulkAccept() {
    setBusy(true)
    try {
      onChange(await api.bulkAccept(analysis.id, reviewer))
      toast.success(`Accepted ${bulkCount} requirements with no open issues.`)
    } catch (e) { toast.error((e as Error).message) } finally { setBusy(false) }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement
      if (e.metaKey || e.ctrlKey || e.altKey || t.closest('input, textarea, select, [role="combobox"], [contenteditable]')) return
      if (document.querySelector('[role="dialog"][data-state="open"], [role="menu"][data-state="open"]')) return   // keys belong to an open Sheet or menu
      const i = shown.findIndex(r => r.id === selected?.id)
      if (e.key === 'j' && shown[i + 1]) setSelectedId(shown[i + 1].id)
      else if (e.key === 'k' && shown[i - 1]) setSelectedId(shown[i - 1].id)
      else if (e.key === 'a') decide('accept')
      else if (e.key === 'r') decide('reject')
      else if (e.key === 'e' && selected) { setDraft(selected.statement); setEditing(true) }
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  function select(id: string) {
    setSelectedId(id)
    if (!desktop) setSheetOpen(true)
  }

  const inspector = selected && (
    <Inspector req={selected} risk={risks.find(k => k.related_requirement_id === selected.id)} all={reqs}
               history={decisions.filter(d => d.target_id === selected.id)} reviewer={reviewer} busy={busy}
               editing={editing} draft={draft} note={note} setEditing={setEditing} setDraft={setDraft} setNote={setNote}
               onDecide={decide} className={desktop ? 'sticky top-32 max-h-[calc(100svh-9rem)] lg:top-20 lg:max-h-[calc(100svh-6.5rem)]' : 'h-full rounded-none shadow-none'} />
  )
  const nextFilter = FILTERS.find(f => f !== 'all' && f !== filter && f !== 'approved' && f !== 'rejected' && counts[f] > 0)

  return (
    <div className="grid gap-5">
      {/* One quiet header row: the donut carries progress, the actions sit beside it. */}
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <Donut size={48} label={`${decided} of ${reqs.length} decided`} parts={[
          { value: counts.approved, tone: 'success' }, { value: counts.rejected, tone: 'danger' },
          { value: counts.needs_clarification, tone: 'warning' }, { value: counts.needs_regeneration, tone: 'neutral' },
          { value: counts.pending_review, tone: 'primary' }]}>
          <CountUp value={decided} />
        </Donut>
        <div className="mr-auto min-w-0">
          <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Review requirements</h1>
          <p className="text-muted-foreground">
            <span className="font-medium text-foreground">{analysis.settings.name}</span>. {decided} of {reqs.length} decided, from a {stakeholder.toLowerCase()} interview analysed in {Math.round(analysis.elapsed)}s.
          </p>
        </div>
        {questions.length > 0 && (
          <Button variant="ghost" onClick={() => setQuestionsOpen(true)}>
            <MessagesSquare aria-hidden />{questions.length} follow-up {questions.length === 1 ? 'question' : 'questions'}
          </Button>
        )}
        {bulkCount > 0 && (
          <Button variant="outline" onClick={bulkAccept} disabled={busy}><CheckCheck aria-hidden />Accept {bulkCount} with no open issues</Button>
        )}
      </header>

      {!reqs.length ? (
        <div className={PANEL}>
          <EmptyState icon={Inbox} title="No requirements were found"
                      action={<Button variant="outline" onClick={onTranscript}><FileText aria-hidden />Back to the transcript</Button>}>
            The model did not extract anything from this transcript. Check that it describes what the system should do, or try the 7B model.
          </EmptyState>
        </div>
      ) : (
        <div className="grid items-start gap-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
          <section aria-label="Requirements" className={cn(PANEL, 'min-w-0 overflow-hidden')}>
            <div className="flex items-center justify-between gap-3 border-b px-4 py-2.5">
              <ToggleGroup type="single" value={view} onValueChange={v => v && setView(v as 'list' | 'risk')} spacing={0}
                           aria-label="View" className="rounded-lg bg-muted p-0.5">
                {([['list', List, 'List'], ['risk', Grid3x3, 'Risk map']] as const).map(([v, Icon, label]) => (
                  <ToggleGroupItem key={v} value={v} size="sm"
                                   className="relative rounded-md! px-3 text-muted-foreground hover:bg-transparent data-[state=on]:bg-transparent data-[state=on]:text-foreground">
                    {view === v && <motion.span layoutId="review-view" transition={spring.snappy} className="absolute inset-0 rounded-md bg-card shadow-sm ring-1 ring-black/5 dark:ring-white/10" />}
                    <Icon className="relative" aria-hidden /><span className="relative">{label}</span>
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
              <span className="text-xs text-subtle-foreground">{view === 'list' ? 'Sorted by risk' : 'Choose a cell to filter'}</span>
            </div>
            {view === 'list' ? (
              <>
                <RequirementList rows={shown} counts={counts} filter={filter} setFilter={setFilter}
                                 selectedId={selected?.id} onSelect={select} flash={flash} />
                {!shown.length && (
                  <EmptyState icon={CheckCheck} title={`Nothing left in ${filter === 'all' ? 'this list' : STATUS[filter as Exclude<Filter, 'all'>].label.toLowerCase()}`}
                              action={nextFilter && <Button variant="outline" size="sm" onClick={() => setFilter(nextFilter)}>
                                Show {STATUS[nextFilter as Exclude<Filter, 'all'>].label.toLowerCase()} ({counts[nextFilter]})</Button>}>
                    {nextFilter ? 'Some requirements still need a decision.' : 'Every requirement has a decision.'}
                  </EmptyState>
                )}
              </>
            ) : (
              <RiskMap risks={risks} cell={cell} setCell={setCell} selectedId={selected?.id} onSelect={select} />
            )}
            <p className="hidden flex-wrap items-center gap-x-2 gap-y-1 border-t bg-muted/60 px-5 py-2.5 text-xs text-subtle-foreground md:flex">
              Keys: <Kbd>j</Kbd><Kbd>k</Kbd> move <Kbd>a</Kbd> accept <Kbd>r</Kbd> reject <Kbd>e</Kbd> edit
            </p>
          </section>

          {desktop && (selected ? inspector : allDecided ? (
            <section className={cn(PANEL, 'grid justify-items-center gap-3 px-6 py-12 text-center md:sticky md:top-32 lg:top-20')}>
              <CheckStamp size={72} />
              <h2 className="text-xl font-semibold tracking-tight">All {reqs.length} requirements decided</h2>
              <p className="max-w-[44ch] text-muted-foreground">
                {counts.approved} approved and {counts.rejected} rejected. Next, choose the delivery model and collect the four sign-offs.
              </p>
              <div className="mt-2 flex flex-wrap justify-center gap-2">
                <Button size="lg" onClick={onNext}><Workflow aria-hidden />Continue to delivery model</Button>
                <Button size="lg" variant="outline" onClick={() => setFilter('all')}>Show all</Button>
              </div>
            </section>
          ) : null)}
        </div>
      )}

      <NextStep ready={allDecided} icon={Workflow} label="Continue to delivery model" onClick={onNext}
                hint={allDecided ? 'Every requirement has a decision.' : !reqs.length ? 'Nothing to review in this analysis.'
                  : `${reqs.length - decided} still open. You can come back to them at any time.`} />

      {!desktop && (
        <Sheet open={sheetOpen && !!selected} onOpenChange={setSheetOpen}>
          <SheetContent side="bottom" className="h-[88svh] gap-0 rounded-t-2xl p-0 pt-10" showCloseButton
                        onOpenAutoFocus={e => { e.preventDefault(); (e.currentTarget as HTMLElement).focus() }}>
            <SheetTitle className="sr-only">Requirement {selected?.id}</SheetTitle>
            {inspector}
          </SheetContent>
        </Sheet>
      )}
      <QuestionsSheet open={questionsOpen} onOpenChange={setQuestionsOpen} questions={questions}
                      stakeholder={stakeholder} onSubmit={onReanalyse} />
    </div>
  )
}
