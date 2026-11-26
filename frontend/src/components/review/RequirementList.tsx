import { Scale, TriangleAlert } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import type { Requirement, Status } from '@/lib/api'
import { spring } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { RiskTag, STATUS, StatusPill, TONE } from '../pills'

export type Filter = Status | 'all'
export const FILTERS: Filter[] = ['pending_review', 'needs_clarification', 'approved', 'rejected', 'needs_regeneration', 'all']
export interface Flash { id: string; tone: 'success' | 'danger' }

export const openIssues = (r: Requirement) =>
  r.quality_issues.length + r.conflicts_with.length + (r.duplicate_of ? 1 : 0)

interface Props {
  rows: Requirement[]; counts: Record<Filter, number>; filter: Filter; setFilter: (f: Filter) => void
  selectedId?: string; onSelect: (id: string) => void; flash: Flash | null
}

// Status filters and ruled rows. The selection marker slides between rows (hover is
// plain CSS: it fires constantly and must not lag). A decided row flashes, then leaves.
export function RequirementList({ rows, counts, filter, setFilter, selectedId, onSelect, flash }: Props) {
  return (
    <>
      <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-1 border-b px-3 py-2.5">
        {FILTERS.filter(f => f === 'all' || f === filter || counts[f] > 0).map(f => (   // empty statuses stay out of the way
          <button key={f} type="button" onClick={() => setFilter(f)} aria-pressed={filter === f}
                  className="relative flex items-center gap-1.5 rounded-full px-2.5 py-1 text-muted-foreground transition-colors hover:text-foreground aria-pressed:font-medium aria-pressed:text-primary">
            {filter === f && <motion.span layoutId="filter-pill" transition={spring.snappy} className="absolute inset-0 rounded-full bg-primary-soft ring-1 ring-primary/25 ring-inset" />}
            <span className="relative">{f === 'all' ? 'All' : STATUS[f].label}</span>
            <span className={cn('relative rounded-full px-1.5 text-xs tabular-nums', filter === f ? 'bg-primary/10' : 'bg-muted')}>{counts[f]}</span>
          </button>
        ))}
      </div>
      <ul>
        <AnimatePresence initial={false}>
          {rows.map((r, i) => {
            const gaps = r.compliance_mappings.filter(m => m.gap).length
            const issues = openIssues(r)
            const current = r.id === selectedId
            return (
              <motion.li key={r.id} layout="position" className="border-b last:border-b-0"
                         initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0, transition: { delay: Math.min(i, 10) * 0.025 } }}
                         exit={{ opacity: 0, x: 40, transition: { duration: 0.2 } }}>
                <button type="button" onClick={() => onSelect(r.id)} aria-current={current}
                        className="relative grid w-full gap-1 px-5 py-3 text-left transition-colors duration-150 hover:bg-muted/60">
                  {current && (
                    <motion.span layoutId="row-selected" transition={spring.snappy} aria-hidden
                                 className="absolute inset-0 bg-primary-soft before:absolute before:inset-y-0 before:left-0 before:w-0.5 before:bg-primary" />
                  )}
                  {flash?.id === r.id && (
                    <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.12 }} aria-hidden
                                 className={cn('absolute inset-0', TONE[flash.tone].soft)} />
                  )}
                  <span className="relative flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-subtle-foreground">{r.id}</span>
                    <RiskTag risk={r.risk_level} />
                    {filter === 'all' && <StatusPill status={r.approval_status} />}
                    <span className="ml-auto flex items-center gap-2.5 text-xs text-subtle-foreground">
                      {gaps > 0 && <span className="flex items-center gap-1" title={`${gaps} policy gap${gaps > 1 ? 's' : ''}`}><Scale className="size-3.5" aria-hidden />{gaps}<span className="sr-only"> policy gaps</span></span>}
                      {issues > 0 && <span className="flex items-center gap-1" title={`${issues} open issue${issues > 1 ? 's' : ''}`}><TriangleAlert className="size-3.5" aria-hidden />{issues}<span className="sr-only"> open issues</span></span>}
                    </span>
                  </span>
                  <span className="relative line-clamp-2 max-w-[72ch]">{r.statement}</span>
                </button>
              </motion.li>
            )
          })}
        </AnimatePresence>
      </ul>
    </>
  )
}
