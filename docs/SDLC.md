# How FinReq was built: Agile–DevSecOps hybrid

FinReq recommends an SDLC model for the projects it analyses. We used the
same engine to pick the model for building FinReq itself, then ran the
project the way that model's workflow says. This page records the choice,
the evidence behind it, and where each phase of the workflow shows up in
this repository.

## 1. Choosing the model

We ran FinReq over its own problem statement
(`backend/data/fixtures/problem_statement.txt`, extracted from
`Problem Statement (1).docx`) and gave it this project's profile
(`docs/finreq_project_profile.json`):

```bash
python backend/cli.py --transcript backend/data/fixtures/problem_statement.txt --role business_analyst \
    --domain FINREQ --no-clarify --profile docs/finreq_project_profile.json --out docs/finreq_self_analysis
```

FinReq extracted 10 requirements of its own (`docs/finreq_self_analysis/SRS.md`)
and ranked the models (`docs/finreq_self_analysis/sdlc_plan.md`):

| Model | Fit |
|---|---|
| **Agile–DevSecOps hybrid** | **64.2%** |
| Agile–V-Model hybrid | 63.7% |
| DevSecOps | 63.2% |
| V-Model | 55.8% |
| Iterative | 55.3% |
| Incremental | 55.3% |
| Spiral | 52.6% |
| Waterfall | 52.1% |
| RAD | 45.8% |
| Agile | 44.2% |

Iterative, Incremental and RAD were added to the engine after this run. The
rows above are the same factors re-scored (the engine is deterministic, so no
model call is needed); they do not change the top recommendation.

We adopted the top recommendation, Agile–DevSecOps hybrid. The margin over
Agile–V-Model is small (0.5 points), so we kept the V-Model's habit of
pairing each level of design with a level of testing (section 4). The
choice still needs the four sign-offs the problem statement asks for
(project manager, architect, security lead, compliance officer). Those are
people on the team, so the committed plan says "awaiting sign-off" until
they record it in the app's **SDLC plan** tab.

This run also found a bug in the engine. The first ranking listed the two
hybrids as a tie at 64%, with Agile–V-Model first. The scores were being
rounded before sorting, so Python's insertion order decided the winner.
Sorting on the unrounded score fixed it
(`test_ranking_orders_by_unrounded_score`).

### Why these profile values

Four factors come from the extracted requirements. The other nine
describe the project, and each value below is backed by something in the
git history:

| Factor | Value | Evidence |
|---|---|---|
| Expected frequency of change | 0.8 | Scope changed every iteration: SDLC deferred then added, default model swapped, a second LLM backend added, the UI redesigned twice |
| Stakeholder availability | 0.9 | The client reviewed and redirected each iteration |
| Budget and schedule pressure | 0.8 | One-month academic timeline |
| Technical uncertainty | 0.8 | Small local LLMs behave unpredictably (sprint 5 found one wrapping JSON in an array) |
| Testing and documentation needs | 0.9 | Graded deliverable: SRS, test evidence and a report are required |
| Need for formal verification | 0.6 | Each requirement needs a traceable test, but there are no formal proofs |
| Project complexity and size | 0.6 | 13 agent roles, 2 LLM backends, a UI, and an eval harness |
| Need for continuous delivery | 0.3 | A prototype with no production deployment |
| Consequence of failure | 0.3 | A prototype: gaps escalate to a human, and no real money moves |

## 2. The workflow we followed

The engine's workflow for Agile–DevSecOps
(`sdlc.workflow("agile_devsecops")`) has five phases. Here is where each
one lives in this repository.

### Planning

- Scope comes from the problem statement. The first increment covers one
  use case (loan origination), as the statement recommends.
- Risks are tracked in the "Known limitations" section of the README (Limitations).
  Each entry records a risk found in a real run and how it was handled.

### Sprints (repeated each iteration)

Each sprint is one commit, tagged `sprint-N`. Every sprint ended with the
gates passing and at least one run against the real model or a real
browser.

| Sprint | Commit | Increment | Verified by | Defects found and fixed |
|---|---|---|---|---|
| 1 | `d8219e6` | Full pipeline, 13 agent roles, knowledge base, storage, artefacts, CLI, UI, eval harness | 58 tests; live run against `qwen2.5-coder-tools:7b` | Risk level was never written back to the requirement |
| 2 | `1b0358d` | Streamlit app driven in a real browser | Regression test plus browser run | SQLite connection crashed across Streamlit threads |
| 3 | `16ecce7` | Faster default model | Live eval of 3B against 7B (precision, recall, F1, time) | none; the speed/recall trade-off was measured and documented |
| 4 | `cf7703c` | Gemini backend (key read from the environment only); live progress; review tabs | 67 tests; browser run | Bulk-accept label showed the wrong count |
| 5 | `d4eea8b` | Restyle following the frontend-design skill | Browser run on the full fixture | The 3B model wrapped JSON objects in arrays (fixed once, in `llm.unwrap_single`); dark text was set on a dark background |
| 6 | `ef2822f` | Paper-ledger theme | Screenshot review against the skill's list of design tells | The first theme matched a forbidden pattern |
| 7 | `36cb03a` | SDLC engine and sign-off; FinReq analysing itself; delivery gates and CI; UI cleanup | 95 tests incl. 11 headless UI tests; live CLI, live eval and real-browser runs | Tied SDLC scores sorted by insertion order; SDLC slider state was lost after Accept; re-analysis overwrote earlier requirement IDs; an empty transcript reached the model |
| 8 | `sprint-8` tag | React + FastAPI front end, rebuilt to a written design system (`DESIGN.md`); Gemini client fixed for current keys and models | 104 tests incl. 8 API tests; full flow in headless Chrome at 1440px and 375px; accesslint audit | Root font size shrank every control; tabs stretched across the page; the mobile header overflowed; selects and the checkbox had no accessible name for the linter; one text colour fell below 4.5:1 on tinted rows; the shadcn CLI was a runtime dependency with high-severity advisories |
| 9 | `sprint-9` tag | Front end v2 after client review called v1 too plain: ink hero with one lazy WebGL gradient, elevated composer, live run view, motion for state changes (`DESIGN.md` v2) | 105 tests incl. 9 API tests; full flow in headless Chrome at 1440px and 375px; accesslint and keyboard-focus probe | The hero painted over the overlapping composer and swallowed its clicks; SDLC sign-offs leaked from one analysis to the next (now scoped by analysis id); hero text lost contrast over the bright part of the gradient |
| 10 | `sprint-10` tag | Projects: every analysis is saved with its transcript, settings and decisions and listed on the start page; final polish | 109 tests incl. 11 API tests (restart persistence, a run cut off by a restart); projects reopened after a real server restart; headless Chrome at 1440px and 375px; accesslint | Analyses lived only in server memory, so a restart lost every run; after a reload "Re-analyse with these answers" sent only the answers and a retry used whatever the composer held; an `?analysis=` link kept reopening the same run; the audit tab mixed every analysis together; the tab row showed a scrollbar (the list kept its variant's 32px height under 40px tabs); on phones the nav pushed the reviewer select past the gutter |
| 11 | `sprint-11` tag | Prism rebrand on a guided four-step flow (light/dark themes, `DESIGN.md` v3) merged with the Projects feature; three new SDLC models (Iterative, Incremental, RAD) | 115 tests incl. 13 API tests (audit scoped to one analysis, built front end never served stale); full flow in headless Chrome at 1440px and 375px; accesslint | The two branches had each rewritten `backend/server.py`'s `Analysis` dataclass and `/api/audit`; reconciled by hand rather than by textual merge, since the UI files had no overlapping lines left to diff |
| 12 | `sprint-12` tag | Groq as a third backend (key from the environment only, model picker fed by the server); a Projects sheet on every screen with delete (the audit trail outlives the project) | 126 tests incl. 15 API tests and 9 Groq client tests; Groq picker and delete flow in the browser against the built front end; all six gates | Groq's model list needs the key, so the browser cannot fetch it (the server lists it and returns ids only); the list included speech, TTS and guard models; `204 No Content` broke the client's JSON parse |

### Secure delivery pipeline (repeated each iteration)

`backend/scripts/gates.py` runs the same gates locally and in CI
(`.github/workflows/ci.yml`). Any failure stops the build:

| Gate | Tool | Result at the end of sprint 12 |
|---|---|---|
| Unit, integration, API and UI tests | pytest | 126 passed |
| Quality benchmarks (no LLM) | `backend/eval/evaluate.py` | quality-check F1 1.0 (min 0.95); conflict accuracy 0.875 (min 0.85) |
| Static security analysis | bandit | no findings at medium severity or higher |
| Secret scan | regex over tracked files | clean |
| Front end | tsc type-check, Vite build, `npm audit --omit=dev` | clean |
| Dependency vulnerabilities | pip-audit | no known vulnerabilities |

```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
python backend/scripts/gates.py
```

### Deployment

The workflow's exit gate is "compliance approval recorded before
production". For this prototype, a release is a tagged commit that passes
every gate and has all four SDLC sign-offs recorded. We have not cut a
release tag; that needs the team's sign-offs first.

### Operations

- **Audit trail.** Every prompt, retrieval and human decision is
  recorded (the app's **Audit trail** tab shows the open project's part).
- **Quality monitoring.** The gates' eval thresholds fail the build if
  detection quality drops below today's level.
- **Model monitoring.** `python backend/eval/evaluate.py --live` re-measures
  extraction quality against the gold set. Results for each model are in
  the README.

## 3. Security practices (the "Sec" in DevSecOps)

| Threat | Mitigation in FinReq | Status |
|---|---|---|
| Personal or account data sent to an LLM | `masking.py` masks values before any prompt and restores them only for the human-facing fields | Implemented and tested |
| A live API key leaking into the repository | `GeminiClient` reads the key only from the environment, with no UI field, flag or config value. The secret-scan gate blocks key-shaped strings | Implemented. During development a live key was pasted into chat; it was not stored anywhere, and its owner was asked to rotate it |
| Prompt injection in a transcript changing what the system does | Agents only return JSON, and that JSON is validated against a schema. Nothing an agent produces becomes final without a human decision | Partial. There is no dedicated injection filter |
| A compliance call made without legal authority | The compliance agent's prompt forbids final legal determinations; gaps escalate to a human | Implemented |
| Approvals changed after the fact | Every decision is written as an `ApprovalRecord` | Partial. SQLite is not append-only or signed |
| Unauthorised reviewers | Sign-off is limited to the four approver roles | Partial. Roles are self-selected; there is no RBAC or MFA (out of scope for the prototype) |
| Vulnerable code or dependencies | bandit and pip-audit gates | Implemented |

## 4. Test levels

We kept the V-Model's pairing of each design level with a test level:

| Design level | Test level | Where |
|---|---|---|
| User needs (problem statement, gold requirements) | Acceptance | `backend/eval/evaluate.py --live` against `eval/gold_requirements.json` |
| System (whole app) | System | Real-browser runs and `backend/tests/test_api.py` (HTTP API via TestClient) |
| Architecture (pipeline wiring) | Integration | `backend/tests/test_pipeline_integration.py` (5) |
| Module design (each agent and module) | Unit | 79 tests across the other `backend/tests/test_*.py` files |
