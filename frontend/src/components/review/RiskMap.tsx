import { motion } from 'motion/react'
import { Button } from '@/components/ui/button'
import type { Risk, RiskItem } from '@/lib/api'
import { spring } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { RISK, RiskPill, TONE } from '../pills'

const LEVELS = ['high', 'medium', 'low'] as const
export const RISK_ORDER: Record<Risk, number> = { critical: 0, high: 1, medium: 2, low: 3 }
export const cellOf = (r: RiskItem) => `${r.likelihood}-${r.impact}`

interface Props {
  risks: RiskItem[]; cell: string | null; setCell: (c: string | null) => void; selectedId?: string; onSelect: (reqId: string) => void
}

// Likelihood by impact. A cell takes the tint of the worst risk inside it, so the
// map always agrees with the pills; position alone does not decide the colour.
export function RiskMap({ risks, cell, setCell, selectedId, onSelect }: Props) {
  const shown = (cell ? risks.filter(r => cellOf(r) === cell) : risks)
    .slice().sort((a, b) => RISK_ORDER[a.risk_level] - RISK_ORDER[b.risk_level])
  return (
    <div className="grid gap-5 p-5">
      <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-3">
        <span className="self-center text-xs text-subtle-foreground [writing-mode:vertical-rl] rotate-180">Likelihood</span>
        <div>
          <div className="grid grid-cols-[3.5rem_repeat(3,minmax(0,1fr))] gap-1.5 text-center text-xs">
            {LEVELS.map(likelihood => (
              <div key={likelihood} className="contents">
                <span className="self-center pr-1 text-right text-subtle-foreground capitalize">{likelihood}</span>
                {LEVELS.slice().reverse().map(impact => {
                  const key = `${likelihood}-${impact}`
                  const inCell = risks.filter(r => cellOf(r) === key)
                  const worst = inCell.map(r => r.risk_level).sort((a, b) => RISK_ORDER[a] - RISK_ORDER[b])[0]
                  const tone = worst ? RISK[worst].tone : null
                  return (
                    <motion.button key={key} type="button" disabled={!inCell.length} whileTap={{ scale: 0.96 }}
                                   onClick={() => setCell(cell === key ? null : key)} aria-pressed={cell === key}
                                   aria-label={`${inCell.length} risks with ${likelihood} likelihood and ${impact} impact${worst ? `, worst ${worst}` : ''}`}
                                   className={cn('grid aspect-[4/3] place-items-center rounded-lg text-lg font-semibold tabular-nums ring-inset transition-shadow',
                                     tone ? cn(TONE[tone].pill, 'ring-1') : 'bg-muted/50 text-subtle-foreground/60',
                                     cell === key && 'ring-2 ring-primary')}>
                      {inCell.length || ''}
                    </motion.button>
                  )
                })}
              </div>
            ))}
            <span />
            {LEVELS.slice().reverse().map(impact => <span key={impact} className="pt-1 text-subtle-foreground capitalize">{impact}</span>)}
          </div>
          <p className="mt-1 text-center text-xs text-subtle-foreground">Impact</p>
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-medium">Risk register{cell && <span className="font-normal text-subtle-foreground">, filtered</span>}</h3>
          {cell && <Button variant="ghost" size="sm" onClick={() => setCell(null)}>Show all {risks.length}</Button>}
        </div>
        <ul className="divide-y rounded-lg ring-1 ring-border">
          {shown.map(r => (
            <motion.li key={r.id} layout="position" transition={spring.smooth}>
              <button type="button" onClick={() => onSelect(r.related_requirement_id)} aria-current={r.related_requirement_id === selectedId}
                      className={cn('grid w-full gap-1 px-4 py-3 text-left transition-colors hover:bg-muted/60',
                        r.related_requirement_id === selectedId && 'bg-primary-soft hover:bg-primary-soft')}>
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-subtle-foreground">{r.related_requirement_id}</span>
                  <RiskPill risk={r.risk_level} />
                  <span className="text-xs text-subtle-foreground">{r.category}, {r.likelihood} likelihood, {r.impact} impact</span>
                </span>
                <span className="line-clamp-2 text-muted-foreground">{r.mitigation}</span>
              </button>
            </motion.li>
          ))}
        </ul>
      </div>
    </div>
  )
}
