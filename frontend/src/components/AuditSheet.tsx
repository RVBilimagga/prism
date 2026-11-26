import { useEffect, useState } from 'react'
import {
  Check, ChevronRight, FileOutput, Gavel, History, MessageSquare, Pencil, RefreshCw, Search, Signature, X, type LucideIcon,
} from 'lucide-react'
import { motion } from 'motion/react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { api, roleLabel, type AuditEvent, type DecisionRecord } from '@/lib/api'
import { spring } from '@/lib/motion'

const EVENT_ICON: Record<string, LucideIcon> = { prompt: MessageSquare, retrieval: Search, decision: Gavel, artifact: FileOutput }
const ACTION: Record<string, [LucideIcon, string]> = {
  accept: [Check, 'accepted'], reject: [X, 'rejected'], modify: [Pencil, 'edited'], regenerate: [RefreshCw, 'asked to regenerate'],
}
const time = (t: string) => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
const pretty = (payload: string) => { try { return JSON.stringify(JSON.parse(payload), null, 2) } catch { return payload } }

interface Props { open: boolean; onOpenChange: (o: boolean) => void; analysisId: string; refreshKey: unknown }

// Every human decision and every model call, newest first. Scoped to this analysis
// by default (GET /api/audit?analysis=<id>).
export function AuditSheet({ open, onOpenChange, analysisId, refreshKey }: Props) {
  const [scope, setScope] = useState<'this' | 'all'>('this')
  const [data, setData] = useState<{ events: AuditEvent[]; decisions: DecisionRecord[] }>()
  useEffect(() => {
    if (!open) return
    setData(undefined)
    api.audit(scope === 'this' ? analysisId : undefined).then(setData).catch(() => setData({ events: [], decisions: [] }))
  }, [open, scope, analysisId, refreshKey])

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 p-0 sm:max-w-xl">
        <SheetHeader className="gap-3 border-b px-6 py-5">
          <div>
            <SheetTitle className="flex items-center gap-2 text-lg"><History className="size-5 text-primary" aria-hidden />Audit trail</SheetTitle>
            <SheetDescription>Every human decision and every model call is recorded, with who made it and when.</SheetDescription>
          </div>
          <ToggleGroup type="single" value={scope} onValueChange={v => v && setScope(v as 'this' | 'all')} spacing={0}
                       aria-label="Scope" className="rounded-lg bg-muted p-0.5">
            {([['this', 'This analysis'], ['all', 'Everything']] as const).map(([v, label]) => (
              <ToggleGroupItem key={v} value={v} size="sm"
                               className="relative rounded-md! px-3 text-muted-foreground hover:bg-transparent data-[state=on]:bg-transparent data-[state=on]:text-foreground">
                {scope === v && <motion.span layoutId="audit-scope" transition={spring.snappy} className="absolute inset-0 rounded-md bg-card shadow-sm ring-1 ring-black/5 dark:ring-white/10" />}
                <span className="relative">{label}</span>
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </SheetHeader>

        <Tabs defaultValue="decisions" className="min-h-0 flex-1 gap-0">
          <TabsList variant="line" className="h-auto w-full justify-start gap-4 border-b px-6 py-0">
            <TabsTrigger value="decisions" className="h-10 flex-none px-0">Decisions {data && <span className="text-subtle-foreground tabular-nums">{data.decisions.length}</span>}</TabsTrigger>
            <TabsTrigger value="events" className="h-10 flex-none px-0">Model calls {data && <span className="text-subtle-foreground tabular-nums">{data.events.length}</span>}</TabsTrigger>
          </TabsList>

          <TabsContent value="decisions" className="min-h-0 overflow-y-auto">
            {!data ? <Loading /> : data.decisions.length ? (
              <ul className="divide-y">
                {data.decisions.slice().reverse().map((d, i) => {
                  const sdlc = d.target_type === 'sdlc_recommendation'
                  const [Icon, verb] = sdlc ? [Signature, 'signed off the delivery model'] : ACTION[d.action] ?? [Gavel, d.action]
                  return (
                    <motion.li key={d.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 12) * 0.02 }}
                               className="flex gap-3 px-6 py-3">
                      <span className="grid size-7 shrink-0 place-items-center rounded-full bg-muted text-muted-foreground"><Icon className="size-3.5" aria-hidden /></span>
                      <div className="min-w-0 flex-1">
                        <p><span className="font-medium">{roleLabel(d.actor_role)}</span> {verb}{' '}
                          <span className="font-mono text-xs">{sdlc ? d.target_id.split(':').pop() : d.target_id}</span></p>
                        {d.note && <p className="text-muted-foreground">{d.note}</p>}
                      </div>
                      <time className="shrink-0 text-xs text-subtle-foreground tabular-nums">{time(d.timestamp)}</time>
                    </motion.li>
                  )
                })}
              </ul>
            ) : <p className="px-6 py-10 text-center text-muted-foreground">No decisions yet. Accept or reject a requirement to start the trail.</p>}
          </TabsContent>

          <TabsContent value="events" className="min-h-0 overflow-y-auto">
            {!data ? <Loading /> : data.events.length ? (
              <ul className="divide-y">
                {data.events.slice().reverse().map(e => {
                  const Icon = EVENT_ICON[e.event_type] ?? MessageSquare
                  return (
                    <Collapsible key={e.id} asChild>
                      <li>
                        <CollapsibleTrigger className="group flex w-full items-center gap-3 px-6 py-2.5 text-left transition-colors hover:bg-muted/60">
                          <span className="grid size-7 shrink-0 place-items-center rounded-full bg-muted text-muted-foreground"><Icon className="size-3.5" aria-hidden /></span>
                          <span className="min-w-0 flex-1">
                            <span className="font-medium capitalize">{e.agent.replace(/_/g, ' ')}</span>{' '}
                            <span className="text-muted-foreground">{e.event_type}</span>
                          </span>
                          <time className="shrink-0 text-xs text-subtle-foreground tabular-nums">{time(e.timestamp)}</time>
                          <ChevronRight className="size-4 shrink-0 text-subtle-foreground transition-transform group-data-[state=open]:rotate-90" aria-hidden />
                        </CollapsibleTrigger>
                        <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
                          <pre className="mx-6 mb-3 max-h-72 overflow-auto rounded-lg bg-muted p-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words text-muted-foreground">{pretty(e.payload)}</pre>
                        </CollapsibleContent>
                      </li>
                    </Collapsible>
                  )
                })}
              </ul>
            ) : <p className="px-6 py-10 text-center text-muted-foreground">No model calls in this scope.</p>}
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  )
}

function Loading() {
  return <div className="grid gap-3 px-6 py-5">{[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-10" />)}</div>
}
