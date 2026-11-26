import {
  Check, Copy, Ellipsis, Gauge, History, ListChecks, Pencil, Quote, RefreshCw, Scale, ScanSearch, X,
  type LucideIcon,
} from 'lucide-react'
import { motion } from 'motion/react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { roleLabel, type Decision, type DecisionRecord, type Requirement, type RiskItem } from '@/lib/api'
import { ease } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { IconTile, Kbd, PANEL } from '../kit'
import { Pill, RiskPill, StatusPill } from '../pills'

const FICTIONAL = / \(fictional prototype document[^)]*\)/g
const humanise = (s: string) => (s.charAt(0).toUpperCase() + s.slice(1)).replace(/_/g, ' ')
export const VERB: Record<string, string> = { accept: 'accepted', reject: 'rejected', modify: 'edited', regenerate: 'asked to regenerate' }

interface Props {
  req: Requirement; risk?: RiskItem; history: DecisionRecord[]; all: Requirement[]; reviewer: string; busy: boolean
  editing: boolean; draft: string; note: string
  setEditing: (e: boolean) => void; setDraft: (d: string) => void; setNote: (n: string) => void
  onDecide: (action: Decision) => void; className?: string
}

// The evidence trace for one requirement and the decision bar. Content cross-fades
// when the selection changes; the bar stays put.
export function Inspector({ req, risk, history, all, reviewer, busy, editing, draft, note, setEditing, setDraft, setNote, onDecide, className }: Props) {
  const startEdit = () => { setDraft(req.statement); setEditing(true) }
  return (
    <section id="inspector" aria-label={`Requirement ${req.id}`} className={cn(PANEL, 'flex min-w-0 flex-col overflow-hidden', className)}>
      <div className="flex-1 overflow-y-auto">
        {/* Keyed fade-in only: j/k swaps content at once, with no exit to wait for. */}
        <motion.div key={req.id} initial={{ opacity: 0, x: 6 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.14, ease }} className="px-6 py-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm text-subtle-foreground">{req.id}</span>
            <StatusPill status={req.approval_status} />
            <RiskPill risk={req.risk_level} />
          </div>
          {editing ? (
            <Textarea value={draft} onChange={e => setDraft(e.target.value)} autoFocus rows={4}
                      aria-label="Edit requirement text" className="mt-3 text-base" />
          ) : (
            <h2 className="mt-3 max-w-[72ch] text-lg leading-snug font-semibold tracking-tight">{req.statement}</h2>
          )}
          <p className="mt-1.5 text-subtle-foreground">
            {humanise(req.priority)} priority. {req.categories.length ? `${req.categories.map(humanise).join(', ')}.` : 'Not categorised.'}
          </p>

          <ol className="relative mt-5 grid gap-5 before:absolute before:top-2 before:bottom-2 before:left-3.5 before:w-px before:bg-border">
            <Step icon={Quote} title={`What the ${roleLabel(req.source_stakeholder).toLowerCase()} said`}>
              {req.source_excerpt
                ? <blockquote className="max-w-[72ch] border-l-2 border-border-strong pl-3 text-muted-foreground italic">“{req.source_excerpt}”</blockquote>
                : <p className="text-warning">No quote links this requirement to the transcript.</p>}
              {req.business_justification && <p className="mt-1.5 text-subtle-foreground">Why: {req.business_justification}</p>}
            </Step>

            <Step icon={Scale} title="Policy evidence">
              {req.compliance_mappings.length ? (
                <ul className="grid gap-2.5">
                  {req.compliance_mappings.map((m, i) => (
                    <li key={i} className="grid gap-0.5">
                      <span className="flex flex-wrap items-center gap-2">
                        <Pill tone={m.gap ? 'warning' : 'success'}>{m.gap ? 'Gap' : 'Mapped'}</Pill>
                        <span className="font-medium">{m.regulation_or_policy.replace(FICTIONAL, '')}</span>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span tabIndex={0} className="cursor-help rounded text-xs text-subtle-foreground tabular-nums underline decoration-dotted underline-offset-2">match {m.confidence.toFixed(2)}</span>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-60 text-pretty">How closely the policy text matches this requirement. Below 0.18 the mapping is treated as a gap for a person to check.</TooltipContent>
                        </Tooltip>
                      </span>
                      <span className="max-w-[72ch] text-muted-foreground">{m.gap ?? m.required_control}</span>
                    </li>
                  ))}
                </ul>
              ) : <p className="text-muted-foreground">No policy was checked.</p>}
            </Step>

            <Step icon={ScanSearch} title="Automated checks">
              {!req.quality_issues.length && !req.conflicts_with.length && !req.duplicate_of ? <p className="text-success">No open issues.</p> : (
                <ul className="grid gap-1 text-muted-foreground">
                  {req.duplicate_of && <li>Possible duplicate of <Ref id={req.duplicate_of} all={all} />.</li>}
                  {req.conflicts_with.map(c => <li key={c}>Conflicts with <Ref id={c} all={all} />.</li>)}
                  {req.quality_issues.map((q, i) => (
                    <li key={i}><span className="text-foreground">{humanise(q.issue_type)}:</span> {q.detail.replace(FICTIONAL, '')}</li>
                  ))}
                </ul>
              )}
            </Step>

            {risk && (
              <Step icon={Gauge} title="Risk assessment">
                <div className="flex flex-wrap gap-1.5">
                  <Pill>{humanise(risk.likelihood)} likelihood</Pill>
                  <Pill>{humanise(risk.impact)} impact</Pill>
                  <Pill>{humanise(risk.category)}</Pill>
                </div>
                <p className="mt-1.5 max-w-[72ch] text-muted-foreground">{risk.mitigation}</p>
              </Step>
            )}

            {!!req.acceptance_criteria.length && (
              <Step icon={ListChecks} title="Acceptance criteria">
                <ul className="grid list-disc gap-1 pl-4 text-muted-foreground marker:text-subtle-foreground">
                  {req.acceptance_criteria.map(a => <li key={a}>{a}</li>)}
                </ul>
              </Step>
            )}

            <Step icon={History} title="Decision history">
              {history.length ? (
                <ul className="grid gap-1.5">
                  {history.slice().reverse().map(d => (
                    <li key={d.id} className="text-muted-foreground">
                      <span className="font-medium text-foreground">{roleLabel(d.actor_role)}</span> {VERB[d.action] ?? d.action}
                      <span className="text-subtle-foreground"> at {new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      {d.note && <span>: {d.note}</span>}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-muted-foreground">No decision yet. Yours is recorded with your role, {roleLabel(reviewer).toLowerCase()}.</p>}
            </Step>
          </ol>
        </motion.div>
      </div>

      <div className="grid gap-2 border-t bg-muted/60 px-6 py-3">
        <Input value={note} onChange={e => setNote(e.target.value)} placeholder="Note for the audit trail (optional)"
               aria-label="Note for the audit trail" className="bg-card" />
        <div className="flex flex-wrap items-center gap-2">
          {editing ? (
            <>
              <Button onClick={() => onDecide('modify')} disabled={busy || !draft.trim() || draft.trim() === req.statement}><Check aria-hidden />Save edit</Button>
              <Button variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
            </>
          ) : (
            <>
              <KeyButton keyName="a" label="Accept" onClick={() => onDecide('accept')} disabled={busy} icon={Check} />
              <KeyButton keyName="r" label="Reject" onClick={() => onDecide('reject')} disabled={busy} icon={X} variant="outline" />
              <KeyButton keyName="e" label="Edit" onClick={startEdit} icon={Pencil} variant="outline" />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" aria-label="More actions" className="ml-auto"><Ellipsis aria-hidden /></Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-52">
                  <DropdownMenuItem onSelect={() => onDecide('regenerate')} disabled={busy}><RefreshCw aria-hidden />Request regeneration</DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onSelect={() => navigator.clipboard.writeText(req.id).then(() => toast.success(`Copied ${req.id}.`), () => toast.error('Copying is blocked in this browser.'))}>
                    <Copy aria-hidden />Copy ID
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          )}
        </div>
      </div>
    </section>
  )
}

// Trace icons stay neutral: the pills and text inside each step already carry the colour.
function Step({ icon, title, children }: { icon: LucideIcon; title: string; children: React.ReactNode }) {
  return (
    <li className="relative grid grid-cols-[1.75rem_minmax(0,1fr)] gap-3">
      <IconTile icon={icon} tone="neutral" className="relative z-10 size-7 ring-4 ring-card [&_svg]:size-3.5" />
      <div className="min-w-0 pt-1">
        <h3 className="mb-1.5 font-medium">{title}</h3>
        {children}
      </div>
    </li>
  )
}

// A requirement id that previews its text on hover or focus.
function Ref({ id, all }: { id: string; all: Requirement[] }) {
  const target = all.find(r => r.id === id)
  if (!target) return <span className="font-mono">{id}</span>
  return (
    <HoverCard openDelay={150} closeDelay={80}>
      <HoverCardTrigger asChild>
        <span tabIndex={0} className="cursor-help rounded font-mono text-foreground underline decoration-dotted underline-offset-2">{id}</span>
      </HoverCardTrigger>
      <HoverCardContent className="w-80">
        <span className="flex items-center gap-2"><span className="font-mono text-xs text-subtle-foreground">{id}</span><RiskPill risk={target.risk_level} /></span>
        <p className="mt-1.5 text-sm">{target.statement}</p>
      </HoverCardContent>
    </HoverCard>
  )
}

function KeyButton({ keyName, label, icon: Icon, variant, ...rest }: {
  keyName: string; label: string; icon: LucideIcon; variant?: 'outline'; onClick: () => void; disabled?: boolean
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant={variant} {...rest}><Icon aria-hidden />{label}</Button>
      </TooltipTrigger>
      <TooltipContent>{label} <Kbd>{keyName}</Kbd></TooltipContent>
    </Tooltip>
  )
}
