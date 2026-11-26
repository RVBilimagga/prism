import { useEffect, useRef, useState } from 'react'
import { CircleCheck, Quote, TriangleAlert } from 'lucide-react'
import { motion, useInView, useReducedMotion } from 'motion/react'
import { ease, spring } from '@/lib/motion'
import { Pill, RiskPill } from './pills'

const QUOTE = ['Any', 'change', 'to', 'the', 'registered', 'phone', '[PHONE_1]', 'should', 'need', 'a', 'second', 'factor.']
const BEAT_MS = [1000, 1400, 1300, 1300, 3200]   // quote, requirement, policy, risk, stamp (held, then the loop restarts)
const BEATS = BEAT_MS.length

// The hero's product demo: one requirement's life in five beats, looping while on
// screen. Every piece stays mounted and fades by beat, so the card keeps one height
// and nothing pops in or out of the layout. Under reduced motion it shows the
// finished frame and never moves.
export default function HeroPreview() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { amount: 0.3 })
  const reduce = useReducedMotion()
  const [tick, setTick] = useState(0)
  const beat = reduce ? BEATS - 1 : tick % BEATS
  const loop = Math.floor(tick / BEATS)
  const at = (n: number) => beat >= n

  useEffect(() => {
    if (reduce || !inView) return
    const timer = setTimeout(() => setTick(t => t + 1), BEAT_MS[tick % BEATS])
    return () => clearTimeout(timer)
  }, [tick, inView, reduce])

  const fade = (on: boolean, delay = 0) => ({
    animate: { opacity: on ? 1 : 0, y: on ? 0 : 6 },
    transition: { duration: on ? 0.45 : 0.3, ease, delay: on ? delay : 0 },
  })

  return (
    <div ref={ref} aria-label="Example: one requirement traced from interview to approval" role="img"
         className="relative rounded-2xl bg-ink/60 p-4 shadow-float ring-1 ring-white/15">
      <div className="flex items-center gap-2 text-[13px] text-ink-muted">
        <Quote className="size-3.5 text-hero-accent" aria-hidden /> Loan officer said
      </div>
      <p key={loop} className="mt-2 text-[15px] leading-relaxed text-ink-foreground">
        {QUOTE.map((w, i) => (
          <motion.span key={i} initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }}
                       transition={{ delay: i * 0.06, duration: 0.25 }}
                       className={w.startsWith('[') ? 'rounded bg-signal/20 px-1 font-mono text-[13px] text-hero-accent' : ''}>
            {w}{' '}
          </motion.span>
        ))}
      </p>

      <motion.div initial={false} {...fade(at(1))} className="mt-4 rounded-xl bg-card p-3.5 text-card-foreground shadow-lift">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-subtle-foreground">LOAN-101</span>
          <motion.span initial={false} {...fade(at(3))}><RiskPill risk="high" /></motion.span>
        </div>
        <p className="mt-1.5 text-[13px] leading-snug font-medium">
          The system shall require re-verification with a second factor before a registered phone number changes.
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <motion.span initial={false} {...fade(at(2))}><Pill tone="success" icon={CircleCheck}>Authentication policy mapped</Pill></motion.span>
          <motion.span initial={false} {...fade(at(2), 0.12)}><Pill tone="warning" icon={TriangleAlert}>KYC policy gap</Pill></motion.span>
        </div>
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted" aria-hidden>
          <motion.div className="h-full origin-left rounded-full bg-danger" initial={false}
                      animate={{ scaleX: at(3) ? 0.78 : 0 }} transition={{ duration: 0.7, ease }} />
        </div>
      </motion.div>

      <motion.div initial={false} animate={{ opacity: at(4) ? 1 : 0, scale: at(4) ? 1 : 1.12 }} transition={at(4) ? spring.smooth : { duration: 0.3 }}
                  className="mt-3 ml-auto flex w-fit -rotate-2 items-center gap-1.5 rounded-lg bg-success-soft px-2.5 py-1 text-[13px] font-semibold text-success ring-2 ring-success/70 ring-inset">
        <CircleCheck className="size-4" aria-hidden /> Accepted by compliance officer
      </motion.div>
    </div>
  )
}
