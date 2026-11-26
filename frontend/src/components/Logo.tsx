import { cn } from '@/lib/utils'

export const BRAND = 'Prism'

// The mark: one beam into a prism, three rays out (one transcript, many requirements).
// Brand colours are fixed; they do not follow the theme. public/favicon.svg is the same drawing.
export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" aria-hidden className={cn('size-7 shrink-0', className)}>
      <rect width="40" height="40" rx="11" fill="var(--brand)" />
      <path d="M24.2 18 36 12.6M25 19.8h11M25.7 21.6 36 27" stroke="var(--signal)" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M25 19.8h11" stroke="var(--hero-accent)" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M4.5 23.4 14.6 20.6" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M19.5 8.5 30.4 29H8.6Z" fill="#fff" strokeLinejoin="round" />
    </svg>
  )
}
