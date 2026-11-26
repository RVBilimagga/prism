import { useState } from 'react'
import { CheckCircle2, ChevronRight, Clock, FolderOpen, Loader2, Plus, Trash2, TriangleAlert } from 'lucide-react'
import { motion } from 'motion/react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { ProjectSummary } from '@/lib/api'
import { ease } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { PANEL, ProgressBar } from './kit'
import { Pill } from './pills'

const when = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })
const RECENT = 5

// A project's place in the flow, in one pill.
function State({ p }: { p: ProjectSummary }) {
  if (p.status === 'running') return <Pill tone="primary" icon={Loader2}>Running</Pill>
  if (p.status === 'failed') return <Pill tone="danger" icon={TriangleAlert}>Stopped</Pill>
  return p.requirements > 0 && p.decided === p.requirements && p.sdlc?.baselined
    ? <Pill tone="success" icon={CheckCircle2}>Complete</Pill>
    : <Pill tone="primary" icon={Clock}>In review</Pill>
}

// Rows are links, so a project can also open in a new tab (Ctrl or Cmd click).
function Row({ p, current, wide, onOpen }: { p: ProjectSummary; current?: boolean; wide?: boolean; onOpen: (id: string) => void }) {
  return (
    <a href={`?analysis=${p.id}`} aria-current={current ? 'page' : undefined}
       onClick={e => { if (!(e.metaKey || e.ctrlKey || e.shiftKey)) { e.preventDefault(); onOpen(p.id) } }}
       className={cn('group grid min-w-0 flex-1 gap-3 px-5 py-3.5 transition-colors duration-150 hover:bg-muted/60 focus-visible:bg-muted/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary',
         wide && 'md:grid-cols-[minmax(0,1fr)_10rem_13rem_6.5rem_1rem] md:items-center md:gap-6',
         current && 'bg-primary-soft hover:bg-primary-soft')}>
      <span className="flex min-w-0 items-start justify-between gap-3">
        <span className="min-w-0">
          <span className="block truncate font-medium">{p.name}</span>
          <span className="text-subtle-foreground tabular-nums">{current ? 'Open now' : when.format(p.started * 1000)}</span>
        </span>
        <span className={cn(wide && 'md:hidden')}><State p={p} /></span>
      </span>
      {p.status === 'done' ? (
        <span className={cn('grid gap-3', wide ? 'md:contents' : 'grid-cols-2')}>
          <span className="grid gap-1.5">
            <span className="text-muted-foreground tabular-nums">{p.decided} of {p.requirements} decided</span>
            <ProgressBar value={p.requirements ? p.decided / p.requirements : 0} label={`${p.name}: requirements decided`} />
          </span>
          <span className="min-w-0">
            <span className="block truncate">{p.sdlc!.name}</span>
            <span className={p.sdlc!.baselined ? 'text-success' : 'text-subtle-foreground tabular-nums'}>
              {p.sdlc!.baselined ? 'Baselined' : `${p.sdlc!.signed} of ${p.sdlc!.approvers} sign-offs`}
            </span>
          </span>
        </span>
      ) : (
        <span className={cn('text-muted-foreground', wide && 'md:col-span-2')}>
          {p.status === 'running' ? 'The agents are still working on this one.' : 'Stopped before it finished. Open it to retry.'}
        </span>
      )}
      {wide && <span className="hidden md:block"><State p={p} /></span>}
      {wide && <ChevronRight className="hidden size-4 text-subtle-foreground transition-transform duration-150 group-hover:translate-x-0.5 md:block" aria-hidden />}
    </a>
  )
}

// Two clicks, so a stray one never deletes: the bin arms, "Delete" confirms, and
// moving focus away disarms. A running analysis cannot be deleted.
function DeleteButton({ p, onDelete }: { p: ProjectSummary; onDelete: (p: ProjectSummary) => void }) {
  const [armed, setArmed] = useState(false)
  if (p.status === 'running') return <span className="w-8 shrink-0" />
  return armed ? (
    <Button size="sm" variant="destructive" autoFocus aria-label={`Confirm: delete ${p.name}`}
            onBlur={() => setArmed(false)} onClick={() => onDelete(p)}>
      Delete
    </Button>
  ) : (
    <Button size="icon" variant="ghost" aria-label={`Delete ${p.name}`} onClick={() => setArmed(true)}
            className="text-subtle-foreground hover:bg-danger-soft hover:text-danger">
      <Trash2 aria-hidden />
    </Button>
  )
}

const rows = (projects: ProjectSummary[], onDelete: (p: ProjectSummary) => void, render: (p: ProjectSummary) => React.ReactNode) =>
  projects.map((p, i) => (
    <motion.li key={p.id} layout="position" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
               transition={{ duration: 0.3, ease, delay: Math.min(i, 8) * 0.03 }} className="flex items-center pr-3">
      {render(p)}
      <DeleteButton p={p} onDelete={onDelete} />
    </motion.li>
  ))

// The start screen's recent projects, on the ink backdrop: the newest few, the rest in the Sheet.
export function ProjectsList({ projects, onOpen, onDelete, onShowAll }: {
  projects: ProjectSummary[]; onOpen: (id: string) => void; onDelete: (p: ProjectSummary) => void; onShowAll: () => void
}) {
  if (!projects.length) return null
  return (
    <section id="projects" aria-labelledby="projects-title" className="mt-12 scroll-mt-4">
      <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-1 text-ink-foreground">
        <div>
          <h2 id="projects-title" className="text-xl font-semibold tracking-tight">
            Recent projects <span className="font-normal text-ink-muted tabular-nums">{projects.length}</span>
          </h2>
          <p className="text-ink-muted">Every analysis is kept with its decisions and sign-offs. Open one to carry on.</p>
        </div>
        {projects.length > RECENT && (
          <Button variant="ghost" onClick={onShowAll} className="text-ink-foreground hover:bg-white/10 hover:text-ink-foreground">
            <FolderOpen aria-hidden />All {projects.length} projects
          </Button>
        )}
      </div>
      <ul className={cn(PANEL, 'mt-4 divide-y overflow-hidden text-foreground')}>
        {rows(projects.slice(0, RECENT), onDelete, p => <Row p={p} wide onOpen={onOpen} />)}
      </ul>
    </section>
  )
}

// Every project, from any screen (top bar). Same pattern as the audit trail.
export function ProjectsSheet({ open, onOpenChange, projects, currentId, onOpen, onDelete, onNew }: {
  open: boolean; onOpenChange: (o: boolean) => void; projects: ProjectSummary[]; currentId?: string
  onOpen: (id: string) => void; onDelete: (p: ProjectSummary) => void; onNew: () => void
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 p-0 sm:max-w-lg">
        <SheetHeader className="gap-3 border-b px-6 py-5">
          <div>
            <SheetTitle className="flex items-center gap-2 text-lg"><FolderOpen className="size-5 text-primary" aria-hidden />Projects</SheetTitle>
            <SheetDescription>Every analysis, newest first, with its decisions and sign-offs.</SheetDescription>
          </div>
          <Button variant="outline" className="w-fit" onClick={onNew}><Plus aria-hidden />New analysis</Button>
        </SheetHeader>
        {projects.length ? (
          <ul className="min-h-0 flex-1 divide-y overflow-y-auto">
            {rows(projects, onDelete, p => <Row p={p} current={p.id === currentId} onOpen={onOpen} />)}
          </ul>
        ) : <p className="px-6 py-10 text-center text-muted-foreground">No projects yet. Analyse a transcript to start one.</p>}
      </SheetContent>
    </Sheet>
  )
}
