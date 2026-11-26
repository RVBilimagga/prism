import { createElement, useRef } from 'react'
import {
  BriefcaseBusiness, ChartColumn, ChevronDown, ClipboardList, DraftingCompass, Gauge, Landmark, Package, Scale, Settings2,
  ShieldCheck, UserRound, type LucideIcon,
} from 'lucide-react'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { roleLabel } from '@/lib/api'
import { cn } from '@/lib/utils'

// One icon per role (reviewer and stakeholder roles from server.py); unknown roles get a person.
const ROLE_ICON: Record<string, LucideIcon> = {
  business_analyst: ChartColumn, product_owner: Package, project_manager: ClipboardList, architect: DraftingCompass,
  security_lead: ShieldCheck, security_officer: ShieldCheck, compliance_officer: Scale, loan_officer: Landmark,
  risk_manager: Gauge, operations_manager: Settings2, customer: UserRound,
}
const iconFor = (role: string) => ROLE_ICON[role] ?? BriefcaseBusiness

interface Props {
  value: string; onChange: (v: string) => void; options: string[]; label: string
  tone?: 'ink' | 'surface'; id?: string; className?: string
}

// A role dropdown. Built on a non-modal DropdownMenu rather than Radix Select:
// Select aligned its list over the trigger (a visible jump, no animation) and locked
// page scroll, which hid the scrollbar and shifted the whole page sideways.
// Opening it moves focus to the current role, so the list starts where you are.
export function RolePicker({ value, onChange, options, label, tone = 'surface', id, className }: Props) {
  const content = useRef<HTMLDivElement>(null)
  return (
    <DropdownMenu modal={false} onOpenChange={open => {
      // After Radix focuses the menu itself (a timer, not rAF: rAF never fires in a background tab).
      if (open) setTimeout(() => content.current?.querySelector<HTMLElement>('[data-state="checked"]')?.focus())
    }}>
      <DropdownMenuTrigger id={id} aria-label={`${label}: ${roleLabel(value)}`}
                           className={cn('group flex items-center gap-2 rounded-lg px-3 text-left text-sm outline-none transition-[background-color,border-color,box-shadow] duration-150 focus-visible:ring-2 focus-visible:ring-ring',
                             tone === 'ink'
                               ? 'h-9 bg-white/10 text-ink-foreground ring-1 ring-white/20 hover:bg-white/15 data-[state=open]:bg-white/15'
                               : 'h-8 border border-input bg-card hover:border-border-strong data-[state=open]:border-ring data-[state=open]:ring-3 data-[state=open]:ring-ring/15',
                             className)}>
        {createElement(iconFor(value), { className: 'size-4 shrink-0 opacity-80', 'aria-hidden': true })}
        <span className="flex-1 truncate">{roleLabel(value)}</span>
        <ChevronDown className="size-4 shrink-0 opacity-70 transition-transform duration-200 group-data-[state=open]:rotate-180" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent ref={content} align="start" sideOffset={6} collisionPadding={12} aria-label={label} className="min-w-60">
        <DropdownMenuLabel className="px-2.5 pt-1.5 pb-1">{label}</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={value} onValueChange={onChange}>
          {options.map(o => {
            const Icon = iconFor(o)
            return (
              <DropdownMenuRadioItem key={o} value={o} className="group/role gap-2.5 py-1.5 pl-1.5 data-[state=checked]:bg-primary-soft data-[state=checked]:text-primary data-[state=checked]:focus:bg-primary-soft data-[state=checked]:focus:text-primary">
                <span className="grid size-7 shrink-0 place-items-center rounded-md bg-muted text-muted-foreground transition-colors group-focus/role:bg-card group-data-[state=checked]/role:bg-card group-data-[state=checked]/role:text-primary">
                  <Icon className="size-3.5" aria-hidden />
                </span>
                {roleLabel(o)}
              </DropdownMenuRadioItem>
            )
          })}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
