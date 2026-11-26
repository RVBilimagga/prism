import { useEffect } from 'react'
import type { LucideIcon } from 'lucide-react'
import { animate, motion, useMotionValue, useReducedMotion, useTransform } from 'motion/react'
import { Button } from '@/components/ui/button'
import { ease, spring } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { TONE, type Tone } from './pills'

// Small shared pieces. Colours come only from tokens (via TONE).

export const PANEL = 'rounded-xl bg-card shadow-panel'

export function IconTile({ icon: Icon, tone = 'primary', className }: { icon: LucideIcon; tone?: Tone; className?: string }) {
  return (
    <span className={cn('grid size-8 shrink-0 place-items-center rounded-lg', TONE[tone].soft, TONE[tone].text, className)}>
      <Icon className="size-4" aria-hidden />
    </span>
  )
}

export function PanelHeader({ icon, tone, title, children, action, className }: {
  icon: LucideIcon; tone?: Tone; title: string; children?: React.ReactNode; action?: React.ReactNode; className?: string
}) {
  return (
    <div className={cn('flex items-start gap-3', className)}>
      <IconTile icon={icon} tone={tone} />
      <div className="min-w-0 flex-1">
        <h2 className="text-base font-semibold">{title}</h2>
        {children && <p className="mt-0.5 max-w-[72ch] text-muted-foreground">{children}</p>}
      </div>
      {action}
    </div>
  )
}

export function Callout({ icon, tone = 'primary', title, children, action, className }: {
  icon: LucideIcon; tone?: Tone; title: string; children?: React.ReactNode; action?: React.ReactNode; className?: string
}) {
  return (
    <div className={cn('flex flex-wrap items-center gap-3 rounded-xl px-4 py-3 ring-1 ring-inset', TONE[tone].pill, className)}>
      <IconTile icon={icon} tone={tone} className="bg-card/70" />
      <div className="min-w-0 flex-1 basis-56">
        <p className="font-medium">{title}</p>
        {children && <div className="text-muted-foreground">{children}</div>}
      </div>
      {action}
    </div>
  )
}

export function EmptyState({ icon, title, children, action }: {
  icon: LucideIcon; title: string; children?: React.ReactNode; action?: React.ReactNode
}) {
  return (
    <div className="grid justify-items-center gap-2 px-6 py-12 text-center">
      <IconTile icon={icon} tone="neutral" className="size-11 rounded-xl [&_svg]:size-5" />
      <p className="mt-1 font-medium">{title}</p>
      {children && <p className="max-w-[48ch] text-muted-foreground">{children}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export const Kbd = ({ children }: { children: React.ReactNode }) => <kbd data-slot="kbd">{children}</kbd>

// value in [0, 1]. scaleX, not width: the bar never triggers layout.
export function ProgressBar({ value, tone = 'primary', label, className, trackClassName }: {
  value: number; tone?: Tone | 'signal'; label: string; className?: string; trackClassName?: string
}) {
  const fill = tone === 'signal' ? 'bg-signal' : TONE[tone].solid
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)}
         className={cn('h-1.5 overflow-hidden rounded-full bg-muted', trackClassName, className)}>
      <motion.div className={cn('h-full origin-left rounded-full', fill)} initial={{ scaleX: 0 }}
                  animate={{ scaleX: Math.min(Math.max(value, 0), 1) }} transition={spring.gentle} />
    </div>
  )
}

export function ProgressRing({ value, size = 44, tone = 'primary', label, children }: {
  value: number; size?: number; tone?: Tone; label: string; children?: React.ReactNode
}) {
  const r = (size - 5) / 2
  return (
    <div role="img" aria-label={label} className="relative grid shrink-0 place-items-center" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} className="absolute inset-0 -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={4} className="stroke-muted" />
        <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={4} strokeLinecap="round"
                       className={TONE[tone].stroke} initial={{ pathLength: 0 }}
                       animate={{ pathLength: Math.min(Math.max(value, 0), 1), opacity: value > 0 ? 1 : 0 }} transition={spring.gentle} />
      </svg>
      <span className="relative text-xs font-semibold tabular-nums">{children}</span>
    </div>
  )
}

// Segments sit end to end around the circle; each draws in from its start angle.
export function Donut({ parts, size = 56, label, children }: {
  parts: { value: number; tone: Tone }[]; size?: number; label: string; children?: React.ReactNode
}) {
  const total = parts.reduce((s, p) => s + p.value, 0) || 1
  const r = (size - 8) / 2
  const starts = parts.map((_, i) => parts.slice(0, i).reduce((s, p) => s + p.value, 0) / total)
  return (
    <div role="img" aria-label={label} className="relative grid shrink-0 place-items-center" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} className="absolute inset-0">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={6} className="stroke-muted" />
        {parts.map((p, i) => {
          const share = p.value / total
          const from = starts[i]
          return share > 0 && (
            <motion.circle key={i} cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={6}
                           transform={`rotate(${from * 360 - 90} ${size / 2} ${size / 2})`} className={TONE[p.tone].stroke}
                           initial={{ pathLength: 0 }} animate={{ pathLength: Math.max(share - 0.012, 0.004) }}
                           transition={{ ...spring.gentle, delay: i * 0.06 }} />
          )
        })}
      </svg>
      <span className="relative text-sm font-semibold tabular-nums">{children}</span>
    </div>
  )
}

// Renders through a motion value, so counting never re-renders React per frame.
export function CountUp({ value, className }: { value: number; className?: string }) {
  const reduce = useReducedMotion()
  const mv = useMotionValue(reduce ? value : 0)
  const shown = useTransform(mv, v => Math.round(v).toLocaleString())
  useEffect(() => {
    if (reduce) { mv.set(value); return }
    const controls = animate(mv, value, { duration: 0.8, ease })
    return () => controls.stop()
  }, [value, reduce, mv])
  return <motion.span className={cn('tabular-nums', className)}>{shown}</motion.span>
}

// A check that draws itself, with one ring ripple: the "done" moment.
export function CheckStamp({ size = 64, tone = 'success' }: { size?: number; tone?: Tone }) {
  const reduce = useReducedMotion()
  const draw = (delay: number) => reduce ? {} : { initial: { pathLength: 0 }, animate: { pathLength: 1 }, transition: { duration: 0.45, delay, ease } }
  return (
    <div className={cn('relative grid place-items-center', TONE[tone].text)} style={{ width: size, height: size }} aria-hidden>
      {!reduce && (
        <motion.span className={cn('absolute inset-0 rounded-full', TONE[tone].soft)} initial={{ scale: 0.6, opacity: 0.9 }}
                     animate={{ scale: 1.5, opacity: 0 }} transition={{ duration: 0.9, delay: 0.5, ease }} />
      )}
      <svg viewBox="0 0 64 64" className="relative size-full">
        <circle cx="32" cy="32" r="30" fill="currentColor" opacity={0.12} />
        <motion.circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" strokeWidth="3" {...draw(0)} />
        <motion.path d="M20 33.5 28.5 42 45 24" fill="none" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round"
                     strokeLinejoin="round" {...draw(0.35)} />
      </svg>
    </div>
  )
}

// The bar that ends every step: what is left, and the way on.
export function NextStep({ ready, hint, label, icon: Icon, onClick }: {
  ready: boolean; hint: string; label: string; icon: LucideIcon; onClick: () => void
}) {
  return (
    <div className={cn(PANEL, 'flex flex-wrap items-center justify-between gap-3 px-5 py-4')}>
      <p className={cn(ready ? 'text-foreground' : 'text-muted-foreground')}>{hint}</p>
      <Button size="lg" variant={ready ? 'default' : 'outline'} onClick={onClick}><Icon aria-hidden />{label}</Button>
    </div>
  )
}
