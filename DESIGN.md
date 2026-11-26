# Prism design system (v3)

Prism (formerly FinReq) is a work tool for business analysts, compliance
officers and security leads. It takes a stakeholder interview, extracts
requirements, checks each one against policy, and asks people to decide. The
interface has to feel like a serious, modern fintech product, and every claim
in it has to show where it came from.

## Why v3

v1 was rejected as "so bad"; v2 added one brand moment (the ink hero) and was
then called nice but bland, with a hard-to-follow flow. v3 keeps v2's identity
and working surfaces and changes four things:

- **Name and mark.** Prism: one transcript in, structured requirements out.
- **Flow.** A guided four-step flow replaces the tabs: Transcript, Review,
  Delivery model, Export.
- **Themes.** Light and dark only. A first visit follows the system; one button switches.
- **Depth.** Lucide icons throughout, more components, and motion that answers
  every action.

## Name and mark

The mark is one beam into a prism and three rays out, on a rounded blue
square. It is drawn once in `frontend/src/components/Logo.tsx` (and copied to
`frontend/public/favicon.svg`). The name is one constant, `BRAND`, in the same file.
The mark's colours are fixed (`--brand`, `--signal`, `--hero-accent`, white)
and do not follow the theme.

## Direction (reference lock)

| Lock | Commitment |
|---|---|
| Brand moment | The ink backdrop with a slow 3D mesh gradient in the token blues. It fills the whole window behind the start, run and failed screens, and the composer floats on it. It is the only WebGL effect. |
| Hero | Two columns. The left holds the headline (word-by-word reveal, last phrase in `--hero-accent`), two calls to action and a trust row. The right holds a live product preview that loops one requirement's life in five beats. |
| Working surface | A light canvas `#f5f6f8` (dark: `#080e1f`) with panels where you interact. The step header is a 64px sticky ink bar with the CSS gradient. |
| Type | Geist and Geist Mono, self-hosted. Display 48–58px at 600 with tight tracking; UI 14px. Mono only for requirement IDs, model names and file names. |
| Accent | Blue for primary actions, focus and selection: `#2563eb` light, `#60a5fa` with ink text in dark. |
| Signal | Sky `#38bdf8`, only for live AI activity: the run checklist, the progress bar, the masked token in the preview. |
| Semantics | Green approved or mapped, amber attention or gap, red rejected or high risk. Pills are tinted and carry a Lucide icon. |
| Icons | `lucide-react` only, 14–16px in UI, inside tinted 32px tiles for section heads. |
| Reject | Indigo or violet, cream with a serif, emoji, decorative stripes, a second WebGL effect, and scroll-jacking. |

## Tokens

All tokens live once in `frontend/src/index.css`: `:root` (light), `.dark` (dark)
and `@theme inline`. Components never hard-code a colour; tone classes are
collected in `TONE` (`frontend/src/components/pills.tsx`).

| Token | Light | Dark | Role |
|---|---|---|---|
| `--ink` / `--ink-foreground` / `--ink-muted` | `#0a1530` / `#fff` / `#b6bccb` | same | Hero and top bar |
| `--brand` | `#2563eb` | same | The logo |
| `--hero-accent` | `#7dd3fc` | same | Hero highlights only |
| `--signal` | `#38bdf8` | same | Live AI activity only |
| `--background` / `--card` / `--popover` | `#f5f6f8` / `#fff` / `#fff` | `#080e1f` / `#0f1830` / `#121c36` | Canvas, panels, overlays |
| `--muted` | `#eef0f4` | `#16213d` | Wells, hover, segmented tracks |
| `--border` / `--border-strong` | `#e3e6ec` / `#cfd4dc` | `#1f2c4b` / `#2c3b5f` | Dividers / keycaps, neutral bars |
| `--foreground` | `#0f172a` | `#e8ecf5` | Primary text |
| `--muted-foreground` / `--subtle-foreground` | `#475569` / `#5b6577` | `#a9b3c9` / `#8e99b3` | Secondary text / metadata |
| `--primary` / `--primary-foreground` / `--primary-soft` | `#2563eb` / `#fff` / `#eef4ff` | `#60a5fa` / `#0a1530` / `#132447` | Actions, focus, selection |
| `--success` on `--success-soft` | `#047857` on `#ecfdf5` | `#34d399` on `#0b2a24` | Approved, mapped |
| `--warning` on `--warning-soft` | `#b45309` on `#fffbeb` | `#fbbf24` on `#2a2007` | Needs attention, gap |
| `--danger` on `--danger-soft` | `#b91c1c` on `#fef2f2` | `#f87171` on `#2d1218` | Rejected, high risk |

Contrast, checked by script for every text pair:

- **Light:** primary text at least 15.6:1, subtle at least 5.1:1, primary on white 5.17:1, semantic pairs at least 4.8:1.
- **Dark:** foreground 13.5–16.2:1, muted 7.6:1 or more, subtle 5.4:1 or more, ink on primary 7.1:1, semantic pairs 6.3–9.6:1.

Other tokens:

- Radius: 10px base. Panels use `rounded-xl`, the composer `rounded-2xl`, and pills and filters are fully rounded.
- Elevation: `shadow-panel`, `shadow-float` (composer, sheets) and `shadow-lift` (preview card). Each includes a 1px ring, which is white at low alpha in dark.
- Every number uses `tabular-nums`.

## Flow

The states are Start (hero and composer), Run (full-height live view), Steps
(sticky bar and work surface) and Failed. Start, run and failed share one fixed,
full-window backdrop that the content scrolls over. Views cross-fade one at a time
(`AnimatePresence mode="wait"`), and the backdrop fades out when the steps open.
Earlier versions morphed the header's height and squashed the hero mid-transition. It is a desktop web app: two-column steps and the
side-by-side inspector start at 768px, and the bottom-sheet inspector exists
only below that.

- **Step rail.** Four steps, each with an icon, a label and progress, for example "3 of 8 decided" or "0 of 4 signed".
  - Done steps show a white check, and connectors fill.
  - The active step has a sliding indicator.
  - Every enabled step is clickable.
  - Below 768px the rail shows only the active step's label.
- **Next step.** Every step ends with a next-step bar that says what is left.
- **Address bar.** `?analysis=<id>&step=<step>` follows you, so a reload lands on the same step.
- **Toasts.** A missing analysis (the server was restarted) shows a toast and returns to Start. Three failed polls in a row show one toast.

## Components

- **Composer:**
  - A header with the project name field, edited in place like a document title.
  - "Upload .txt" and drag-and-drop, with an overlay.
  - The sample loader.
  - A Switch for follow-up questions.
  - A Local/Gemini ToggleGroup with a sliding thumb.
  - Ctrl or Cmd+Enter to analyse.
  - The Gemini-key warning as a Callout.
- **Projects:** two views of the same rows (`ProjectsList.tsx`).
  - On the start screen, "Recent projects" (the newest five) sits under the composer, with its heading in ink type on the backdrop and "All N projects" when there are more.
  - From any screen, the top bar's Projects button opens a right Sheet, the same pattern as the audit trail. It lists every project, marks the open one ("Open now", primary tint) and has "New analysis", which clears the composer.
  - Each row is a link (Ctrl or Cmd click opens a new tab): name and start time, "N of M decided" on the shared `ProgressBar`, the chosen delivery model with its sign-off count (green "Baselined" when all four are in), and a status pill (In review, Complete, Running, Stopped). Rows stagger in.
  - The Review header leads with the project name.
- **Run:**
  - The thinking orb and the current stage as a blur cross-fade.
  - An elapsed CountUp and the signal ProgressBar.
  - The full stage checklist: done ticks pop in, the active stage shimmers, pending stages are hollow.
- **Review:** kept deliberately quiet.
  - One header row: a status Donut that carries progress, the title with "x of y decided", a ghost button for the follow-up questions (it opens a Sheet), and bulk accept. There is no separate progress bar or banner.
  - A List or Risk map toggle.
  - Status filters show only statuses that have requirements, plus All; the active pill slides between them.
  - Rows mark risk with a coloured dot and a word (`RiskTag`), not a pill, so a long list is not a column of red. Gap and issue counts are small icons.
  - The selection marker slides; hover is plain CSS. A decided row flashes its outcome, then leaves.
  - The risk map tints each cell by the worst risk inside it.
- **Inspector:**
  - Header: ID, status and risk pills; priority and categories as one muted sentence under the statement.
  - The evidence trace, each step with a small neutral icon (the content carries the colour): what was said, policy evidence, automated checks, risk assessment, acceptance criteria, decision history.
  - Requirement IDs open a HoverCard.
  - Decision buttons have Tooltips with their keys.
  - A DropdownMenu holds "Request regeneration" and "Copy ID".
  - It becomes a CheckStamp completion card when nothing is left.
  - Below 1024px it opens as a bottom Sheet.
- **Delivery model:**
  - Ten models; the top five show, with "Show all 10".
  - Rows reorder with layout animation, and bars spring with `scaleX`.
  - "In favour" and "Against" columns.
  - The workflow as a numbered Timeline (a real sequence), with each exit gate highlighted.
  - The sticky sign-off card has a ProgressRing, initials avatars and a "Switch to" button per waiting approver. It shows a CheckStamp when baselined.
  - The profile sliders sit in a Collapsible.
- **Export:**
  - A readiness checklist and the nine files, each with an icon and one line.
  - The download button morphs into "Downloaded".
- **Audit trail:**
  - A right Sheet with two tabs, Decisions and Model calls.
  - A scope toggle (This analysis or Everything).
  - Model-call rows expand to their pretty-printed JSON.
- **Building blocks:**
  - Shared primitives live in `frontend/src/components/kit.tsx`.
  - shadcn primitives live in `components/ui/`: Sheet, Tooltip, HoverCard, DropdownMenu (via `RolePicker` for role choices), ToggleGroup, Collapsible, Switch, Skeleton, Slider, Tabs.

## Motion

- **Presets.** One file, `frontend/src/lib/motion.ts`:
  - `ease` = `[0.22, 1, 0.36, 1]`
  - springs `snappy` (thumbs, markers), `smooth` (layout, panels) and `gentle` (bars, rings, numbers)
  - `rise`
  - `slide` (steps, with the direction as `custom`)
- **Transform and opacity only.** Bars use `scaleX`, rings use `pathLength`, and numbers render through a motion value (no React render per frame).
- **One orchestrated moment.** On the start screen the headline, copy, buttons and chips rise in sequence, the composer follows, and the preview loops while on screen. It uses opacity and transform only; the earlier per-word blur reveal stuttered. Everything else answers an action.
- **Keyboard actions never wait on animation.** `a`/`r` send the decision at once, and `j`/`k` swap the inspector with a 140ms fade and no exit.
- **Exits are faster than entries.** Steps exit in 180ms and enter in 350ms.
- **Theme switch.** One button (sun or moon) runs the switch in `document.startViewTransition` as a 240ms cross-fade. It is instant when the page is hidden or under reduced motion.
- **Reduced motion.** `MotionConfig reducedMotion="user"`, a global CSS collapse, the gradient off, and the preview frozen on its final frame. The spotlight and the scroll drift are off.
- **Scroll.** Nothing is scroll-linked: the content scrolls over a fixed backdrop. There is no scroll-jacking.

## Performance

- **WebGL.** three.js and the gradient are a lazy chunk, memoised so the 1s poll never re-renders it.
  - It mounts once with `lazyLoad={false}`. The library's default unmounted it off-screen, so scrolling back restarted it (a visible reload).
  - Grain is off.
  - It loads 900ms after first paint, so shader compilation never lands on the intro animation, then fades in over 1.2s.
  - Its backdrop is fixed, so the canvas is always viewport-sized and never leaves the screen.
  - The steps use the CSS gradient only.
- **No blur over the gradient.** Nothing on the hero uses `backdrop-filter`: blurring over a moving WebGL canvas re-blurs every frame. The glass look is translucent ink.
- **Spotlight.** A pre-painted glow moved by a spring (transforms only), not a gradient repainted on every pointer move. It listens on the window.
- **Preview loop.** Every piece stays mounted and fades by beat, so the card keeps one height and nothing pops in or out.
- **Dropdowns and scroll lock.** Role pickers are a non-modal DropdownMenu (`RolePicker`), with no scroll lock and a scale from the trigger. `html { scrollbar-gutter: stable }` plus a `margin-right: 0` override keep Sheets from shifting the page.
- **No flash.** An inline script in `index.html` sets the theme class before first paint. next-themes' own script is made an inert data block.
- **No stale builds.** `backend/server.py` serves `frontend/dist` through `AppFiles`: `index.html` and other unhashed files get `Cache-Control: no-cache`, and hashed `assets/` get a year and `immutable`. Without this, browsers kept running an old build after `npm run build`.

## Accessibility

- accesslint is clean on the start, review, delivery and export screens.
- Radix ToggleGroup roots drop their inline `outline: none`, so `:focus-visible` shows.
- Selects, the switch and segmented controls carry `aria-labelledby` or `aria-label`.

## Copy

- Use plain verbs and sentence case, and write from the reviewer's side.
- There are no eyebrow labels, no middle-dot meta strings and no trailing arrows on buttons. A leading Lucide icon names the destination instead.
