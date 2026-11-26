import { FolderOpen, History } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { BRAND, Logo } from './Logo'
import { RolePicker } from './RolePicker'
import { ThemeToggle } from './ThemeToggle'

interface Props {
  variant: 'hero' | 'bar'; rail?: React.ReactNode; onAudit?: () => void; onHome: () => void; onProjects: () => void
  reviewer: string; setReviewer: (r: string) => void; roles: string[]
}

// Brand, the step rail (once an analysis exists) and the global controls. Always on ink.
export function TopBar({ variant, rail, onAudit, onHome, onProjects, reviewer, setReviewer, roles }: Props) {
  return (
    <div className={cn('mx-auto flex w-full max-w-7xl flex-wrap items-center gap-x-5 gap-y-2 px-4 md:px-8', variant === 'bar' ? 'py-2.5' : 'py-4')}>
      <button type="button" onClick={onHome} aria-label={`${BRAND}, start screen`}
              className="flex items-center gap-2.5 rounded-lg text-[17px] font-semibold tracking-tight transition-opacity hover:opacity-90">
        <Logo /> {BRAND}
      </button>
      {rail && <div className="order-last w-full lg:order-none lg:w-auto lg:flex-1">{rail}</div>}
      <div className="ml-auto flex items-center gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" onClick={onProjects} aria-label="Projects" className="h-9 text-ink-foreground hover:bg-white/10 hover:text-ink-foreground">
              <FolderOpen aria-hidden /><span className="sr-only 2xl:not-sr-only">Projects</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent className="2xl:hidden">Projects</TooltipContent>
        </Tooltip>
        {onAudit && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" onClick={onAudit} className="h-9 text-ink-foreground hover:bg-white/10 hover:text-ink-foreground">
                <History aria-hidden /><span className="sr-only 2xl:not-sr-only">Audit trail</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent className="2xl:hidden">Audit trail</TooltipContent>
          </Tooltip>
        )}
        <ThemeToggle />
        <span className="hidden text-ink-muted 2xl:inline">Reviewing as</span>
        <RolePicker tone="ink" label="Reviewing as" value={reviewer} onChange={setReviewer} options={roles} className="w-48" />
      </div>
    </div>
  )
}
