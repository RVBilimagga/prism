import { useEffect, useState } from 'react'
import {
  BookOpen, Check, CircleCheck, CircleDashed, CircleHelp, Download, FileSpreadsheet, FileText, Link2, PackageCheck, Scale,
  ShieldAlert, Waypoints, Workflow, type LucideIcon,
} from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { api, type Analysis } from '@/lib/api'
import { ease, spring } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { PANEL, PanelHeader } from './kit'

// What is in the zip (src/finreq/artifacts.py writes these names).
const FILES: [string, LucideIcon, string][] = [
  ['SRS.md', FileText, 'The software requirements specification, each requirement with its evidence.'],
  ['user_stories.md', BookOpen, 'User stories with their acceptance criteria.'],
  ['requirements.csv', FileSpreadsheet, 'Every requirement with its categories, risk and review status.'],
  ['traceability_matrix.csv', Waypoints, 'Each requirement traced to who said it and the regulations it touches.'],
  ['compliance_matrix.csv', Scale, 'Requirement-to-policy mappings, including the gaps.'],
  ['risk_register.csv', ShieldAlert, 'Risks with likelihood, impact and mitigation.'],
  ['open_issues.md', CircleHelp, 'Clarifications, conflicts and policy gaps still to close.'],
  ['assumptions_dependencies.md', Link2, 'The assumptions and dependencies the requirements rely on.'],
  ['sdlc_plan.md', Workflow, 'The ranked models, the chosen workflow and who has signed it off.'],
]

export function ExportStep({ analysis }: { analysis: Analysis }) {
  const reqs = analysis.requirements ?? []
  const sdlc = analysis.sdlc!
  const decided = reqs.filter(r => r.approval_status === 'approved' || r.approval_status === 'rejected').length
  const unclear = reqs.filter(r => r.approval_status === 'needs_clarification').length
  const questions = analysis.questions?.length ?? 0
  const [downloaded, setDownloaded] = useState(false)
  useEffect(() => {
    if (!downloaded) return
    const t = setTimeout(() => setDownloaded(false), 3000)
    return () => clearTimeout(t)
  }, [downloaded])

  const checks: { ok: boolean | null; label: string; value: string }[] = [
    { ok: reqs.length > 0 && decided === reqs.length, label: 'Requirements decided', value: `${decided} of ${reqs.length}` },
    { ok: unclear === 0, label: 'Waiting for clarification', value: unclear ? `${unclear} open` : 'None' },
    { ok: sdlc.baselined, label: 'Delivery model signed off', value: `${sdlc.signed.length} of ${sdlc.approvers.length}` },
    { ok: null, label: 'Follow-up questions suggested', value: questions ? `${questions}` : 'None' },
  ]
  const ready = checks.every(c => c.ok !== false)

  return (
    <div className="grid gap-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">Export the artefacts</h1>
        <p className="mt-0.5 max-w-[72ch] text-muted-foreground">
          One zip with every document. It reflects the decisions made so far, so you can export a draft at any point.
        </p>
      </header>

      <div className="grid items-start gap-5 md:grid-cols-[18rem_minmax(0,1fr)] lg:grid-cols-[21rem_minmax(0,1fr)]">
        <section className={cn(PANEL, 'p-5')}>
          <PanelHeader icon={PackageCheck} tone={ready ? 'success' : 'warning'} title={ready ? 'Ready to export' : 'Not final yet'}>
            {ready ? 'Every decision and sign-off is in.' : 'You can still export; the documents show what is open.'}
          </PanelHeader>
          <ul className="mt-4 grid gap-1">
            {checks.map((c, i) => (
              <motion.li key={c.label} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.06 * i, duration: 0.3, ease }}
                         className="flex items-center gap-3 rounded-lg px-2 py-2">
                {c.ok === null ? <CircleHelp className="size-4.5 text-subtle-foreground" aria-hidden />
                  : c.ok ? <CircleCheck className="size-4.5 text-success" aria-hidden /> : <CircleDashed className="size-4.5 text-warning" aria-hidden />}
                <span className="flex-1">{c.label}</span>
                <span className="tabular-nums text-muted-foreground">{c.value}</span>
              </motion.li>
            ))}
          </ul>
        </section>

        <section className={cn(PANEL, 'overflow-hidden')}>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
            <div>
              <h2 className="text-base font-semibold">{FILES.length} files in one zip</h2>
              <p className="text-muted-foreground">prism-{analysis.id}.zip</p>
            </div>
            <Button asChild size="lg" className="min-w-44">
              <a href={api.exportUrl(analysis.id)} download onClick={() => { setDownloaded(true); toast.success('Download started.') }}>
                <AnimatePresence mode="wait" initial={false}>
                  <motion.span key={String(downloaded)} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                               transition={spring.snappy} className="flex items-center gap-1.5">
                    {downloaded ? <><Check aria-hidden />Downloaded</> : <><Download aria-hidden />Download artefacts</>}
                  </motion.span>
                </AnimatePresence>
              </a>
            </Button>
          </div>
          <ul className="divide-y">
            {FILES.map(([name, Icon, text], i) => (
              <motion.li key={name} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.035 * i, duration: 0.3, ease }}
                         className="flex items-start gap-3 px-5 py-3">
                <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground"><Icon className="size-4" aria-hidden /></span>
                <span className="min-w-0">
                  <span className="block font-mono text-[13px]">{name}</span>
                  <span className="text-muted-foreground">{text}</span>
                </span>
              </motion.li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
