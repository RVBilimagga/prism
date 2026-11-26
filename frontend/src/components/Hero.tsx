import { useEffect, useState } from 'react'
import {
  ChevronRight, ClipboardPaste, EyeOff, GitCompareArrows, ListChecks, ListPlus, Scale, ScrollText, ShieldAlert,
  ShieldCheck, Sparkles, Tags, WifiOff, Workflow, type LucideIcon,
} from 'lucide-react'
import { motion, useReducedMotion, useSpring } from 'motion/react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { rise } from '@/lib/motion'
import HeroPreview from './HeroPreview'

const LEAD = 'From stakeholder interview to requirements'
const PHRASE = 'an auditor can trace.'

const PIPELINE: [LucideIcon, string, string][] = [
  [EyeOff, 'Mask', 'Names, accounts, cards, PAN, IFSC, phones and emails are masked before any model reads the text.'],
  [ListPlus, 'Extract', 'Turns what people said into requirement records, each with its source quote.'],
  [Tags, 'Classify', 'Labels each one: functional, security, privacy, regulatory and more.'],
  [ListChecks, 'Check quality', 'Flags vague wording, missing justification and untestable criteria.'],
  [GitCompareArrows, 'Find conflicts', 'Finds duplicates and contradictions between requirements.'],
  [Scale, 'Map to policy', 'Retrieves policy evidence and maps each requirement to a control, or flags a gap.'],
  [ShieldAlert, 'Assess risk', 'Scores likelihood and impact, and routes risky items to the right officer.'],
  [Workflow, 'Recommend SDLC', 'Ranks ten delivery models for this project and drafts the workflow.'],
]

const TRUST: [LucideIcon, string][] = [
  [WifiOff, 'Runs offline on a local model'],
  [ShieldCheck, 'Personal data masked first'],
  [ScrollText, 'Every decision audited'],
]

// The start screen's hero copy and live preview, over App's fixed backdrop.
// One calm entrance: blocks rise in sequence (opacity and transform only). The old
// per-word blur reveal, plus a scroll-linked drift, stuttered while WebGL started.
export function StartHero({ onTrySample, onPasteOwn }: { onTrySample: () => void; onPasteOwn: () => void }) {
  return (
    <motion.div initial="hidden" animate="show" transition={{ staggerChildren: 0.08 }}
                className="mx-auto grid w-full max-w-7xl items-center gap-x-14 gap-y-8 px-4 pt-6 pb-12 md:px-8 md:pt-12 md:pb-14 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.85fr)]">
      <div>
        <motion.h1 variants={rise} className="max-w-3xl text-[2.5rem] leading-[1.05] font-semibold tracking-[-0.03em] sm:text-5xl lg:text-[3.25rem]">
          {LEAD} <span className="text-hero-accent">{PHRASE}</span>
        </motion.h1>
        <motion.p variants={rise} className="mt-5 max-w-xl text-base text-ink-muted md:text-lg">
          Thirteen agents extract each requirement, check it, map it to policy and score its risk.
          Every decision stays with a person.
        </motion.p>
        <motion.div variants={rise} className="mt-7 flex flex-wrap gap-3">
          <Button size="lg" onClick={onTrySample}
                  className="h-11 rounded-xl bg-ink-foreground px-5 text-[15px] text-ink shadow-float hover:bg-ink-foreground/90 active:scale-[0.98]">
            <Sparkles aria-hidden /> Try the sample interview
          </Button>
          <Button size="lg" variant="ghost" onClick={onPasteOwn}
                  className="h-11 rounded-xl bg-white/10 px-5 text-[15px] text-ink-foreground ring-1 ring-white/20 hover:bg-white/15 hover:text-ink-foreground active:scale-[0.98]">
            <ClipboardPaste aria-hidden /> Paste your own
          </Button>
        </motion.div>
        <motion.ul variants={rise} className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-[13px] text-ink-muted">
          {TRUST.map(([Icon, text]) => (
            <li key={text} className="flex items-center gap-2"><Icon className="size-4 text-hero-accent" aria-hidden />{text}</li>
          ))}
        </motion.ul>
      </div>

      <motion.div variants={rise} className="hidden lg:block"><HeroPreview /></motion.div>

      <motion.ol variants={rise} aria-label="What happens to a transcript" className="flex flex-wrap items-center gap-1.5 text-xs lg:col-span-2">
        {PIPELINE.map(([Icon, label, tip], i) => (
          <li key={label} className="flex items-center gap-1.5">
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 ring-1 ring-white/15 transition-colors duration-150 hover:bg-white/20">
                  <Icon className="size-3.5 text-hero-accent" aria-hidden />{label}
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-64 text-pretty">{tip}</TooltipContent>
            </Tooltip>
            {i < PIPELINE.length - 1 && <ChevronRight className="size-3 text-ink-muted" aria-hidden />}
          </li>
        ))}
      </motion.ol>
    </motion.div>
  )
}

// A soft glow that trails the pointer over the fixed backdrop. The gradient is painted
// once; a spring moves the layer with transforms, so nothing repaints per move. It
// listens on the window because the backdrop sits behind the content.
const GLOW = 640
export function Spotlight() {
  const reduce = useReducedMotion()
  const x = useSpring(0, { stiffness: 140, damping: 22, mass: 0.5 })
  const y = useSpring(0, { stiffness: 140, damping: 22, mass: 0.5 })
  const [on, setOn] = useState(false)
  useEffect(() => {
    if (reduce || !matchMedia('(hover: hover) and (pointer: fine)').matches) return
    let inside = false
    const move = (e: PointerEvent) => {
      const [nx, ny] = [e.clientX - GLOW / 2, e.clientY - GLOW / 2]
      if (inside) { x.set(nx); y.set(ny) } else { x.jump(nx); y.jump(ny); inside = true }   // appear under the pointer, don't fly in
      setOn(true)
    }
    const leave = () => { inside = false; setOn(false) }
    window.addEventListener('pointermove', move)
    document.documentElement.addEventListener('pointerleave', leave)
    return () => {
      window.removeEventListener('pointermove', move)
      document.documentElement.removeEventListener('pointerleave', leave)
    }
  }, [reduce, x, y])
  return (
    <motion.div aria-hidden style={{ x, y, width: GLOW, height: GLOW }} initial={{ opacity: 0 }} animate={{ opacity: on ? 1 : 0 }}
                transition={{ duration: 0.4 }}
                className="pointer-events-none absolute top-0 left-0 rounded-full bg-[radial-gradient(circle,color-mix(in_oklch,var(--hero-accent)_14%,transparent),transparent_62%)]" />
  )
}
