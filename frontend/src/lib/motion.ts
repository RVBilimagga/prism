import type { Transition, Variants } from 'motion/react'

// Shared motion presets (DESIGN.md v3, Motion). Animate transform and opacity only.
export const ease = [0.22, 1, 0.36, 1] as const

export const spring = {
  snappy: { type: 'spring', stiffness: 520, damping: 42 },   // thumbs, markers, toggles
  smooth: { type: 'spring', stiffness: 260, damping: 32 },   // layout changes, panels
  gentle: { type: 'spring', stiffness: 140, damping: 22 },   // bars, rings, numbers
} satisfies Record<string, Transition>

export const rise: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease } },
}

// Step transitions: pass the direction (1 forward, -1 back) as `custom`.
export const slide: Variants = {
  enter: (dir: number) => ({ opacity: 0, x: dir * 16 }),
  center: { opacity: 1, x: 0, transition: { duration: 0.28, ease } },
  exit: (dir: number) => ({ opacity: 0, x: dir * -16, transition: { duration: 0.14, ease } }),
}
