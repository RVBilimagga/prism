import { Check, Download, FileText, ListChecks, Workflow, type LucideIcon } from 'lucide-react'
import { motion } from 'motion/react'
import { spring } from '@/lib/motion'
import { cn } from '@/lib/utils'

export type Step = 'transcript' | 'review' | 'delivery' | 'export'
export const STEPS: { key: Step; label: string; icon: LucideIcon }[] = [
  { key: 'transcript', label: 'Transcript', icon: FileText },
  { key: 'review', label: 'Review', icon: ListChecks },
  { key: 'delivery', label: 'Delivery model', icon: Workflow },
  { key: 'export', label: 'Export', icon: Download },
]
export interface StepInfo { hint: string; done: boolean; disabled?: boolean }

// The guided flow, on the ink bar. Any enabled step is one click away; the order
// and the ticks say what to do next.
export function StepRail({ active, info, onSelect }: { active: Step; info: Record<Step, StepInfo>; onSelect: (s: Step) => void }) {
  return (
    <nav aria-label="Steps">
      <ol className="flex items-center justify-between gap-1 sm:justify-start">
        {STEPS.map(({ key, label, icon: Icon }, i) => {
          const s = info[key]
          const current = active === key
          return (
            <li key={key} className="flex items-center gap-1">
              {i > 0 && (
                <span className="h-px w-3 overflow-hidden bg-white/20 sm:w-5 xl:w-8" aria-hidden>
                  <motion.span className="block h-full origin-left bg-white/80" initial={false}
                               animate={{ scaleX: info[STEPS[i - 1].key].done ? 1 : 0 }} transition={spring.gentle} />
                </span>
              )}
              <button type="button" disabled={s.disabled} onClick={() => onSelect(key)} aria-current={current ? 'step' : undefined}
                      className="group relative flex items-center gap-2 rounded-full py-1 pr-3 pl-1 text-left outline-offset-2 transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:bg-transparent">
                {current && (
                  <motion.span layoutId="rail-active" transition={spring.snappy} className="absolute inset-0 rounded-full bg-white/12 ring-1 ring-white/20" />
                )}
                <span className={cn('relative grid size-7 shrink-0 place-items-center rounded-full transition-colors',
                  s.done ? 'bg-ink-foreground text-ink' : current ? 'bg-brand text-white' : 'text-ink-muted ring-1 ring-white/25')}>
                  {s.done ? <Check className="size-3.5" strokeWidth={3} aria-hidden /> : <Icon className="size-3.5" aria-hidden />}
                </span>
                <span className={cn('relative leading-tight', !current && 'hidden md:grid', current && 'grid')}>
                  <span className={cn('text-[13px] font-medium whitespace-nowrap', current ? 'text-ink-foreground' : 'text-ink-muted group-hover:text-ink-foreground')}>{label}</span>
                  <span className="hidden text-[11px] whitespace-nowrap text-ink-muted tabular-nums sm:block lg:hidden xl:block">{s.hint}</span>
                </span>
                {!current && <span className="sr-only md:hidden">{label}, {s.hint}</span>}
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
