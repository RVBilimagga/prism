# ARCHITECTURE.md


## Commands

```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt   # runtime deps + bandit/pip-audit/httpx for the gates
npm ci --prefix frontend                       # front-end deps (Node 24)

npm run build --prefix frontend && python backend/server.py   # the app: http://127.0.0.1:8000 (API + built React front end)
npm run dev --prefix frontend                  # front-end dev server on :5173, proxies /api to backend/server.py on :8000
npm run lint --prefix frontend                 # oxlint (not a gate; `npm run build` runs `tsc -b`, so type errors fail the web gate)

python -m pytest                          # no Ollama needed (FakeLLMClient; API via TestClient)
python -m pytest backend/tests/test_quality.py    # a single test file
python -m pytest backend/tests/test_quality.py::test_clean_requirement_has_no_issues  # a single test
python backend/scripts/gates.py                   # every gate: tests, eval thresholds, bandit, secret scan, web build + npm audit, pip-audit
python backend/scripts/gates.py --skip-audit      # same, offline (pip-audit needs network)

python backend/cli.py --transcript backend/data/fixtures/loan_officer_interview.txt --role loan_officer --domain LOAN \
    --profile backend/data/fixtures/loan_project_profile.json --out out
python backend/cli.py --transcript backend/data/fixtures/loan_officer_interview.txt --role loan_officer --backend gemini --model gemini-3.5-flash-lite

python backend/eval/evaluate.py                   # offline benchmarks (no Ollama needed)
python backend/eval/evaluate.py --live            # + live extraction eval (needs `ollama serve` running)
```

Tests use `pyproject.toml`'s `pythonpath = ["backend"]` (run pytest from the repo root), so `import finreq...`
and `import server` work directly from `backend/tests/` without an editable install. CI
(`.github/workflows/ci.yml`) runs exactly `python backend/scripts/gates.py`. The eval
gate's floors (quality-check F1 >= 0.95, conflict accuracy >= 0.85) sit at
today's measured values, so any regression in the rule-based agents fails it.

Other settings in `backend/finreq/config.py` read from the environment: `FINREQ_LLM_BACKEND`
(`ollama`|`gemini`), `FINREQ_OLLAMA_HOST`, and `FINREQ_DB_PATH` (default
`finreq.db` in the working directory; it holds every saved analysis).

**Ollama** must be running locally for `backend/server.py`, `backend/cli.py` and `--live`
eval (`ollama serve`). Default model is `qwen2.5:3b-instruct`
(`ollama pull qwen2.5:3b-instruct`; override with `FINREQ_MODEL`, the
sidebar field, or `--model`). `request_timeout_s = 600` covers slow
models on modest hardware.

### Model choice (measured, not assumed)

Results from `backend/eval/evaluate.py --live` against the loan-officer fixture
(reports in `eval/results/`, gitignored — rerun to regenerate):

| model | precision | recall | F1 | regulatory coverage | time |
|---|---|---|---|---|---|
| `qwen2.5:3b-instruct` (default), after the `unwrap_single` fix | 0.9 | 0.562 | 0.692 | 1.0 | 81s |
| `qwen2.5:3b-instruct`, before that fix | 0.778 | 0.438 | 0.56 | 0.75 | 70s |
| `hhao/qwen2.5-coder-tools:7b` (`FINREQ_FALLBACK_MODEL`) | 0.8 | 0.75 | 0.774 | 0.5 | 211s |

Each row is a single run; small models vary run to run. The 3B model is
~3x faster but folds several stakeholder statements into one coarser
requirement, so it misses more of the gold set. The "before" row
undercounts regulatory coverage partly because of the JSON-wrapping bug
(compliance mappings were silently dropped). Use the default for
iteration and demos; use the 7B model when recall matters more than time.

### A second backend: Gemini (API)

`build_llm_client(backend, model)` (`backend/finreq/llm.py`) is the single
entry point `backend/server.py`, `backend/cli.py` and `backend/eval/evaluate.py` use
to pick a backend. Default Gemini model: `gemini-3.5-flash-lite`, picked
from the free-tier quota table, not from model rank. One analysis of the
sample interview makes about 32 calls. Flash-lite allows 15 a minute and 500
a day (about 15 analyses a day), and it ran end to end live. `gemini-3.8-flash`
and the other non-lite Flash models allow 5 a minute and 20 a day, so one
analysis cannot finish on a free key. The Antigravity quota is for Google's
managed agent API, not `generateContent`. Override the model with
`FINREQ_GEMINI_MODEL` or the UI's model field. The key goes in
the `x-goog-api-key` header, the form Google documents for both standard
keys and the service-account-bound "auth keys" AI Studio has issued since
May 2026 (they look like `AQ.…`). Never put it in `?key=`: URLs end up in
exception text, logs and the UI. HTTP errors become an `LLMError` that
carries Google's message, never the key.

**Credential handling is deliberate and non-negotiable:** `GeminiClient`
reads its key **only** from the `GEMINI_API_KEY` environment variable.
The user sets it either in their shell or in a `.env` file at the repo root,
which `config.load_dotenv()` copies into the environment at import (a value
set in the shell wins). `.env` is gitignored, so it is never committed, and
the secret-scan gate in `backend/scripts/gates.py` (it scans files git would track)
skips it while failing the build on key-shaped strings anywhere else. Nothing
accepts a key as a constructor argument, CLI flag, API route or UI field.
Keep it that way. `backend/tests/test_gemini_client.py` covers
request/response shape and the missing-key path with a mocked
`requests.post`.

**Free-tier keys hit limits in a single analysis** (found live): one run
makes more calls than the 15-requests-a-minute free tier allows (429), and
new models shed load under demand (503). `GeminiClient.generate` retries up to 6
times, waiting Google's `RetryInfo` delay but never less than 5, 10, 20,
40, 60, 60s: Google's hint can be under a second while the minute is still
full; a wait over 60s (an exhausted daily quota) fails at once with
Google's message. Expect a free-tier run to take minutes, not seconds.

### A third backend: Groq (API)

`GroqClient` (`llm.py`) calls Groq's OpenAI-compatible
`https://api.groq.com/openai/v1/chat/completions`. Default model
`openai/gpt-oss-120b` (override with `FINREQ_GROQ_MODEL`, `--model`, or the
UI's model dropdown); gpt-oss models get `reasoning_effort: low`, because
reasoning tokens count against the free plan's 8K tokens a minute. The
dropdown is `GET /api/groq/models`: Groq's model list needs the key, so the
server fetches it (only ids reach the browser), drops speech, TTS and guard
models, puts the default first, and caches it an hour; without a key or
offline it offers the default alone. The key follows the Gemini rule exactly:
`GROQ_API_KEY` from the shell or `.env` only, sent as a Bearer header.
Requests use JSON mode (`response_format: json_object`). The free plan allows
about 30 requests a minute and 1K a day per model (an analysis makes ~32
calls), so 429/498/503 wait Groq's `retry-after` but at least 5, 10, 20, 40,
60, 60s; a `retry-after` over 60s (a spent daily quota) fails at once. Not
yet measured with `eval --live`.

## Project goal

An agentic, multi-agent LLM system for automated requirements engineering
and SDLC-model recommendation in the financial sector, per
`Problem Statement (1).docx` (text copy: `backend/data/fixtures/problem_statement.txt`).
It extracts requirements from a stakeholder transcript, classifies and
quality-checks them, maps them to sample policies with cited evidence,
assesses risk, ranks SDLC models for the project, and generates
SRS/user-stories/traceability/compliance/risk/SDLC-plan artefacts — with a
human approval step before anything is final. Scope: **loan origination**,
one use case, per the problem statement's "begin with one" guidance.

**How FinReq itself was built** — model choice (Agile–DevSecOps hybrid,
picked by running FinReq on its own problem statement), sprint log,
pipeline gates, threat table, test levels — is in `docs/SDLC.md`. Keep its
sprint table current: one row per tagged `sprint-N` commit.

## Architecture

```
backend/finreq/    the Python package (agents live together in agents/)
  config.py        Settings (model, thresholds, DB path) — single source of truth
  models.py        pydantic models: Requirement, RiskItem, ComplianceMapping, Evidence,
                   QualityIssue, ApprovalRecord, AuditEvent + enums
  masking.py       Regex PII masking/unmasking (emails, cards, PAN, IFSC, phone, account no.)
  llm.py           LLMClient: OllamaClient + GeminiClient (via build_llm_client()) +
                   FakeLLMClient (tests). generate_json() repair-retries invalid JSON;
                   unwrap_single() undoes small models wrapping an object in a 1-item array.
  retrieval.py     KnowledgeBase: backend/data/knowledge_base/*.md, TF-IDF + cosine retrieval
  storage.py       Store: SQLite for requirements/risks/approvals/audit log, plus
                   analyses (the web UI's projects: settings, transcript, stages,
                   SDLC factors and choice, and the ids of their requirements/risks)
  artifacts.py     Documentation agent: SRS.md, user_stories.md, *.csv, open_issues.md,
                   sdlc_plan.md (when given)
  sdlc.py          SDLC selection engine: derive_factors() (4 from requirements, 9 from a
                   project profile), rank() (weighted MCDA, explainable), workflow()
                   (phases with financial controls built in), render_plan()
  pipeline.py      run_pipeline(): the orchestrator — wires every agent below
  agents/
    base.py            Agent base class + AgentContext (shared llm/kb/store + audit log)
    interaction.py     Stakeholder Interaction Agent — clarifying questions (LLM)
    extraction.py      Requirement Extraction Agent (LLM)
    classification.py  Classification Agent — multi-label categories (LLM)
    quality.py         Quality-Check Agent (rule-based)
    conflict.py        Conflict-Detection Agent — TF-IDF duplicates/contradictions (rule-based)
    compliance.py      Compliance Agent — retrieval-grounded mapping, low confidence = gap (LLM)
    security.py        Security/Privacy Agent — tagging + missing-control check (rule-based)
    risk.py            Risk-Analysis Agent — scores, sets requirement.risk_level (rule-based)
    validation.py      Validation Agent — NEEDS_CLARIFICATION vs PENDING_REVIEW (rule-based)
    approval.py        record_decision() for requirements; record_sdlc_signoff() /
                       sdlc_signoffs() for the SDLC choice (SDLC_APPROVER_ROLES)

backend/server.py  FastAPI app: /api routes over the same functions (analyses run in a
                   background thread; the client polls for stage progress), and serves
                   frontend/dist via AppFiles (index.html no-cache, hashed assets immutable,
                   so a rebuild is never hidden by browser cache). Every analysis is
                   saved as it starts, finishes and changes its SDLC choice, and
                   reloaded by create_app(), so GET /api/analyses (the project list)
                   survives a restart; one still "running" at load lost its thread and
                   reopens as failed. create_app(store, llm_factory) is injectable for
                   tests.
backend/cli.py     Headless run: per-stage progress, requirements, SDLC top 3, artefacts.
                   --backend/--model pick the LLM; --profile sets the SDLC project profile.
frontend/          React 19 + Vite + Tailwind v4 + shadcn/ui front end (see "UI" below)
DESIGN.md          The design system the front end (Prism) follows: tokens, themes, flow, motion
backend/scripts/gates.py   Delivery gates, shared by local runs and CI

backend/data/knowledge_base/*.md          Sample policies (fictional; provenance header on each)
backend/data/fixtures/                    loan_officer_interview.txt, loan_project_profile.json,
                                  problem_statement.txt
docs/SDLC.md                      How FinReq was built (see Project goal)
docs/finreq_project_profile.json  FinReq's own SDLC project profile
docs/finreq_self_analysis/        FinReq's analysis of its own problem statement (evidence)
backend/eval/                     evaluate.py + quality/conflict benchmarks + gold requirements
```

**Orchestration model:** `pipeline.run_pipeline()` *is* the coordinator. It
builds one `AgentContext` and calls each agent in a fixed order: mask ->
(optional) interaction -> extraction -> classification -> quality ->
conflict -> compliance -> security -> risk -> validation -> unmask ->
persist. Agents mutate requirements in place; `RiskAnalysisAgent.run()`
both returns a `RiskItem` *and* sets `requirement.risk_level` (they must
never disagree). Requirement IDs continue from the highest number already
in the store for that prefix, so a re-analysis never overwrites an earlier
requirement or detaches its approvals. Empty transcripts are rejected
before any model call.

**SDLC is deliberately not part of `run_pipeline()`:** it depends on a
human-supplied project profile and is recomputed whenever a slider moves.
Callers run it after the pipeline: `rank(derive_factors(reqs, profile))`.
`rank()` sorts on the unrounded score (two models can round to the same
percentage). A choice is baselined only when all four
`SDLC_APPROVER_ROLES` have signed off that specific model.

**Rule-based vs. LLM agents, deliberately:** quality, conflict, risk,
security, validation and the SDLC engine are pure Python — those judgments
must be explainable and reproducible for an audit. Interaction,
extraction, classification and compliance need a model.

**Masking boundary:** the raw transcript is masked once at ingestion;
every LLM-facing agent sees only masked text. Real values are restored
(`_unmask_requirement`) after every agent has run, on the human-facing
fields only.

**Retrieval:** TF-IDF + cosine similarity, not a vector database — a
dependency-free choice for a fully offline prototype. `DOMAIN_STOP_WORDS`
and `SETTINGS.low_confidence_threshold = 0.18` were tuned empirically
against the sample KB.

## UI (frontend/ — React)

**Read `DESIGN.md` (v3) before touching the front end.** The web UI is
branded **Prism** (`BRAND` and the mark in `frontend/src/components/Logo.tsx`); the
Python package, CLI and `FINREQ_*` variables keep the FinReq
name. v1 was rejected as too plain and v2 as bland. v3 keeps v2's ink hero,
with its lazy ShaderGradient, and its white panels. It adds light and dark
themes (next-themes, `.dark` tokens; the toggle has two states, first visit
follows the system), Lucide icons and a guided four-step flow. It is a
desktop app: two-column steps start at 768px. Blue marks actions and
selection (`#2563eb`, `#60a5fa` in dark); sky `--signal` is reserved for live
AI activity. Tokens live once in `frontend/src/index.css`; never hard-code a colour.

- `frontend/src/App.tsx`: the state machine (start, run, failed, steps). Start,
  run and failed sit on one fixed, full-window ink backdrop (gradient, WebGL,
  spotlight) that the content scrolls over; views cross-fade with
  `AnimatePresence mode="wait"`. On the steps the header is a sticky ink bar.
  Holds polling, the scoped decision history, and `?analysis=<id>&step=<step>`
  (replaceState). The analysis id is also kept in localStorage. Reopening
  restores the saved transcript and settings, so retry and re-analysis repeat
  the original run.
- `components/TopBar.tsx`, `StepRail.tsx`: brand, step rail (Transcript,
  Review, Delivery model, Export with progress hints), a Projects button that
  returns to the start screen's project list, audit button, theme toggle,
  "Reviewing as".
- `components/Hero.tsx` (`StartHero`, `Spotlight`) and `HeroPreview.tsx`:
  headline, calls to action, trust row, pipeline chips with tooltips, the
  looping product preview (all pieces stay mounted; static under reduced motion).
- `components/HeroGradient.tsx`: the only WebGL effect, `React.lazy` and
  `memo` (the 1s poll must not re-render it). Start and run screens only.
  Keep `lazyLoad={false}`: the library default unmounts the canvas off-screen,
  so scrolling back up restarted the animation. Never put `backdrop-blur` on
  anything over it (re-blurs every frame).
- `components/RolePicker.tsx`: role dropdowns on a non-modal DropdownMenu.
  Radix Select was dropped: it aligned over the trigger with no animation and
  locked scroll, which shifted the page. `index.css` keeps
  `scrollbar-gutter: stable` for Sheets.
- `components/InputPanel.tsx`: the composer (project name field, upload and
  drop a .txt, sample, Switch, Local/Gemini/Groq ToggleGroup, a model
  `<select>` for Groq, Ctrl/Cmd+Enter).
- `components/ProjectsList.tsx`: one row design, two views over
  `GET /api/analyses`. `ProjectsList` shows the newest five under the composer
  (heading in ink type on the backdrop). `ProjectsSheet`, opened from the top
  bar's Projects button on every screen, lists them all, marks the open one and
  has "New analysis" (clears the composer). Rows show review progress, delivery
  model and sign-offs, and status. They are links (`?analysis=<id>`), so one
  opens in a new tab. Each has a two-click delete (`DELETE /api/analyses/<id>`,
  refused while running) that drops the project only: its requirements,
  approvals and audit events stay, and the deletion is itself an audit event.
- `components/RunView.tsx`: the live run; `PLANNED_STAGES` mirrors the
  labels `pipeline.run_pipeline` announces (update both together).
- `components/review/`: `ReviewStep` (filters, keys j/k/a/r/e, mobile
  inspector Sheet), `RequirementList`, `RiskMap` (cell tint = worst risk in
  the cell), `Inspector` (evidence trace, decision bar), `QuestionsSheet`.
- `DeliveryStep`, `ExportStep`, `AuditSheet` — scoped to the open project
  with `GET /api/audit?analysis=<id>` (decisions on its requirement ids and
  SDLC scope, model calls logged while it ran); a toggle switches to
  everything.
- `components/kit.tsx`: shared primitives (IconTile, PanelHeader, Callout,
  EmptyState, Kbd, ProgressBar, ProgressRing, Donut, CountUp, CheckStamp,
  NextStep). `pills.tsx` holds `TONE` and the status and risk pills.
  `lib/motion.ts` holds the shared springs, easing and variants.
- **Backdrop stacking:** the backdrop is `fixed inset-0 -z-10`, so nothing
  between it and the page may set an opaque background on the hero views (the
  composer is the only card there). The sticky bar's `z-30` applies on the
  steps only.
- **Keyboard shortcuts** are ignored while a Sheet or menu is open
  (`[role=dialog|menu][data-state=open]`), and they never wait on an animation.
- **Motion:** use `motion/react` only, wrapped in `MotionConfig
  reducedMotion="user"`. Do not add a second animation library.
- **Accessibility:** accesslint is clean on start, review, delivery and
  export once the page settles. Radix selects and switches need
  `aria-labelledby`. The ToggleGroup root drops Radix's inline
  `outline: none` (see `ui/toggle-group.tsx`). accesslint cannot see a
  sliding `layoutId` background, so active text must pass contrast against
  the panel itself.
- The `shadcn` CLI is a devDependency (build-time CSS only).

## Known limitations (found via real runs, not hypothetical)

- **Small models wrap a single JSON object in a 1-item array.** Fixed once
  at the root: `llm.unwrap_single()`, used by interaction, classification
  and compliance.
- **The 3B model sometimes omits every business justification in a run.**
  Every requirement is then flagged incomplete and routed to "needs
  clarification", and the derived SDLC "requirement stability" factor drops
  to 0. The rules are working as intended; rerun or use the 7B model.
- **Derived "requirement stability" measures how clear the extracted
  requirements are, not how often scope changes.** Volatility over time
  belongs in the human-set "expected frequency of change" factor.
- **Audit events carry no analysis id**, so the audit tab picks a run's
  model calls by time window. Two runs started at the same moment would
  show each other's calls. Decisions are matched exactly.
- **TF-IDF duplicate detection misses paraphrases** (conflict benchmark
  case C2). Fixing this needs semantic embeddings.
- **The 7B model is conservative about compliance relevance** — clearly
  related policies get escalated as gaps. Don't lower the threshold to
  hide it; gaps escalate to a human, which is the safe failure mode.
- **Sample KB documents are fictional** and labelled as such. Compliance
  output is not legal advice.
- **`Store` needs `check_same_thread=False`** (the API serves
  requests and runs analyses on different threads). Re-check if SQLite is ever swapped out.

## Non-negotiable constraints (from the problem statement)

- **Human-in-the-loop.** `agents/approval.py` is the only place
  `approval_status` changes after validation — always an explicit human
  action (accept/reject/edit/regenerate). The SDLC choice needs four
  sign-offs. The compliance agent never makes a final legal determination.
- **Audit everything.** Every LLM call and retrieval is an `AuditEvent`;
  every human decision (requirements and SDLC sign-offs) is an `ApprovalRecord`.
- **Security controls implemented:** PII masking before any LLM call,
  offline retrieval, full audit trail, environment-only API keys, and the
  bandit/pip-audit/secret-scan gates. **Not implemented** (out of scope
  for a prototype): RBAC, MFA, encryption at rest, session isolation.
