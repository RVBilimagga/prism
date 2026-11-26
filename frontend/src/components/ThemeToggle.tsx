import { flushSync } from 'react-dom'
import { Moon, Sun } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useTheme } from 'next-themes'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { spring } from '@/lib/motion'

// Two themes, one button. A first visit follows the system; a click picks light or
// dark. The page cross-fades between them (View Transitions API, 240ms in
// index.css); without it, or under reduced motion, the switch is instant.
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const dark = resolvedTheme === 'dark'

  function toggle() {
    const next = dark ? 'light' : 'dark'
    const apply = () => {
      document.documentElement.classList.toggle('dark', next === 'dark')   // before the snapshot, not after React's effect
      flushSync(() => setTheme(next))
    }
    // A hidden document gets no frames, so a transition's callback would wait: switch at once.
    if (!document.startViewTransition || document.visibilityState !== 'visible'
        || matchMedia('(prefers-reduced-motion: reduce)').matches) apply()
    else document.startViewTransition(apply)
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" onClick={toggle} aria-label={dark ? 'Switch to the light theme' : 'Switch to the dark theme'}
                className="relative grid size-9 shrink-0 place-items-center overflow-hidden rounded-lg bg-white/10 text-ink-foreground ring-1 ring-white/20 transition-[background-color,transform] duration-150 hover:bg-white/15 active:scale-[0.96]">
          <AnimatePresence initial={false} mode="popLayout">
            <motion.span key={dark ? 'moon' : 'sun'} className="grid place-items-center" transition={spring.snappy}
                         initial={{ y: 12, opacity: 0, rotate: -60 }} animate={{ y: 0, opacity: 1, rotate: 0 }} exit={{ y: -12, opacity: 0, rotate: 60 }}>
              {dark ? <Moon className="size-4" aria-hidden /> : <Sun className="size-4" aria-hidden />}
            </motion.span>
          </AnimatePresence>
        </button>
      </TooltipTrigger>
      <TooltipContent>{dark ? 'Light theme' : 'Dark theme'}</TooltipContent>
    </Tooltip>
  )
}
