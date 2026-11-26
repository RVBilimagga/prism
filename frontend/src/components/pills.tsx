import {
  CircleAlert, CircleCheck, CircleDot, CircleHelp, CircleX, Clock, RefreshCw, Siren, TriangleAlert, type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Risk, Status } from '@/lib/api'

export type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'primary'

// One place for tone classes, so pills, tiles, rings and bars agree.
export const TONE: Record<Tone, { pill: string; soft: string; text: string; solid: string; stroke: string }> = {
  neutral: { pill: 'bg-muted text-muted-foreground ring-border', soft: 'bg-muted', text: 'text-muted-foreground',
             solid: 'bg-subtle-foreground', stroke: 'stroke-subtle-foreground' },
  success: { pill: 'bg-success-soft text-success ring-success-border', soft: 'bg-success-soft', text: 'text-success',
             solid: 'bg-success', stroke: 'stroke-success' },
  warning: { pill: 'bg-warning-soft text-warning ring-warning-border', soft: 'bg-warning-soft', text: 'text-warning',
             solid: 'bg-warning', stroke: 'stroke-warning' },
  danger: { pill: 'bg-danger-soft text-danger ring-danger-border', soft: 'bg-danger-soft', text: 'text-danger',
            solid: 'bg-danger', stroke: 'stroke-danger' },
  primary: { pill: 'bg-primary-soft text-primary ring-primary/25', soft: 'bg-primary-soft', text: 'text-primary',
             solid: 'bg-primary', stroke: 'stroke-primary' },
}

export function Pill({ tone = 'neutral', icon: Icon, className, children }: {
  tone?: Tone; icon?: LucideIcon; className?: string; children: React.ReactNode
}) {
  return (
    <span className={cn('inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset transition-colors duration-200',
      TONE[tone].pill, className)}>
      {Icon && <Icon className="size-3 shrink-0" aria-hidden />}
      {children}
    </span>
  )
}

export const STATUS: Record<Status, { label: string; tone: Tone; icon: LucideIcon }> = {
  pending_review: { label: 'To review', tone: 'primary', icon: Clock },
  needs_clarification: { label: 'Needs clarification', tone: 'warning', icon: CircleHelp },
  approved: { label: 'Approved', tone: 'success', icon: CircleCheck },
  rejected: { label: 'Rejected', tone: 'danger', icon: CircleX },
  needs_regeneration: { label: 'Regeneration requested', tone: 'neutral', icon: RefreshCw },
}

export const RISK: Record<Risk, { label: string; tone: Tone; icon: LucideIcon }> = {
  critical: { label: 'Critical risk', tone: 'danger', icon: Siren },
  high: { label: 'High risk', tone: 'danger', icon: TriangleAlert },
  medium: { label: 'Medium risk', tone: 'warning', icon: CircleAlert },
  low: { label: 'Low risk', tone: 'neutral', icon: CircleDot },
}

export const StatusPill = ({ status }: { status: Status }) => (
  <Pill tone={STATUS[status].tone} icon={STATUS[status].icon}>{STATUS[status].label}</Pill>
)
// For dense lists: a coloured dot and a word, so a column of rows is not a column of red pills.
const DOT: Record<Risk, string> = { critical: 'bg-danger', high: 'bg-danger', medium: 'bg-warning', low: 'bg-subtle-foreground' }
export const RiskTag = ({ risk }: { risk: Risk }) => (
  <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
    <span aria-hidden className={cn('size-1.5 rounded-full', DOT[risk], risk === 'critical' && 'ring-2 ring-danger/25')} />
    {RISK[risk].label}
  </span>
)
export const RiskPill = ({ risk }: { risk: Risk }) => (
  <Pill tone={RISK[risk].tone} icon={RISK[risk].icon}>{RISK[risk].label}</Pill>
)
