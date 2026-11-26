# Prism

**Agentic requirements engineering and SDLC-model recommendation for financial services.**

Prism turns a stakeholder interview into reviewed, policy-mapped,
risk-assessed requirements. It recommends a delivery model for the project and
generates the supporting documentation. Nothing becomes final until a person
accepts it.

> The web UI is branded *Prism*. The Python package, CLI and `FINREQ_*`
> environment variables keep the project's original name, **FinReq**.

## Contents

- [Overview](#overview)
- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Using the application](#using-the-application)
- [Command line](#command-line)
- [Configuration](#configuration)
- [Project layout](#project-layout)
- [Quality and verification](#quality-and-verification)
- [Security and governance](#security-and-governance)
- [Limitations](#limitations)
- [Further reading](#further-reading)

## Overview

| Input | Output |
|---|---|
| A stakeholder interview transcript and an optional project profile | Classified, quality-checked requirements with policy evidence and risk scores |
| Reviewer decisions (accept, reject, edit, regenerate) | An audit trail of every decision and model call |
| Four role sign-offs on the chosen delivery model | SRS, user stories, traceability matrix, compliance matrix, risk register, SDLC plan |

The first use case is **loan origination**, following the problem statement's
advice to begin with one domain. Prism was built with the SDLC model it
recommended for itself, an Agile–DevSecOps hybrid. See
[docs/SDLC.md](docs/SDLC.md).

## How it works

A fixed-order pipeline coordinates specialised agents. Judgments that must be
explainable and reproducible for an audit are rule-based. Language tasks use a
model.

```
transcript → mask PII → interaction* → extraction* → classification*
           → quality → conflict → compliance* → security → risk → validation
           → unmask → persist → human review → SDLC selection → artefacts
                                                   (* = LLM agent)
```

| Agent | Type | Responsibility |
|---|---|---|
| Interaction | LLM | Clarifying questions for the stakeholder |
| Extraction | LLM | Pulls atomic requirements from the transcript |
| Classification | LLM | Multi-label categories |
| Quality | Rules | Completeness, ambiguity and testability checks |
| Conflict | Rules (TF-IDF) | Duplicate and contradiction detection |
| Compliance | LLM + retrieval | Maps requirements to policy evidence; low confidence becomes a gap |
| Security / Privacy | Rules | Tagging and missing-control checks |
| Risk | Rules | Risk score and level |
| Validation | Rules | Routes to *needs clarification* or *pending review* |
| Approval | Human | The only place approval status changes |

SDLC selection is deliberately separate from the pipeline. It depends on a
human-supplied project profile and is recomputed as the profile changes. A
weighted multi-criteria model ranks ten delivery models with an explainable
score. The choice is baselined only after the project manager, architect,
security lead and compliance officer have each signed off.

## Quick start

**Prerequisites:** Python 3.11+, Node.js 24+, and one model backend.

| Backend | Setup |
|---|---|
| [Ollama](https://ollama.com) (local, default) | `ollama pull qwen2.5:3b-instruct`, then `ollama serve` |
| Google Gemini | Set `GEMINI_API_KEY` in your shell or in a gitignored `.env` file |
| Groq | Set `GROQ_API_KEY` in your shell or in a gitignored `.env` file |

```bash
pip install -r backend/requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
python backend/server.py
```

Open <http://127.0.0.1:8000>.

For front-end development, run `npm run dev --prefix frontend`. It serves on
port 5173 and proxies `/api` to the backend on port 8000.

## Using the application

The interface is a guided four-step flow. Light and dark themes follow the
system setting.

1. **Transcript.** Name the project and paste or upload a transcript, or use
   the sample interview. Choose a backend, then analyse (`Ctrl/Cmd+Enter`).
   The run view shows each pipeline stage live.
2. **Review.** Triage requirements in a list or on the risk map. The inspector
   shows the evidence trace: the stakeholder's words, policy evidence,
   automated checks, risk assessment and decision history. Keys: `j`/`k` move,
   `a` accept, `r` reject, `e` edit.
3. **Delivery model.** Compare ranked SDLC models, adjust the project profile
   and collect the four role sign-offs.
4. **Export.** Download every artefact as one zip. The audit trail lists each
   decision and model call.

Every analysis is saved under **Projects** and survives a server restart.
Deleting a project removes it from the list. Its decisions stay in the audit
trail.

## Command line

```bash
python backend/cli.py \
    --transcript backend/data/fixtures/loan_officer_interview.txt \
    --role loan_officer --domain LOAN \
    --profile backend/data/fixtures/loan_project_profile.json \
    --out out
```

Use `--backend gemini|groq|ollama` and `--model <name>` to select the LLM.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `FINREQ_LLM_BACKEND` | `ollama`, `gemini` or `groq` | `ollama` |
| `FINREQ_MODEL` | Ollama model | `qwen2.5:3b-instruct` |
| `FINREQ_GEMINI_MODEL` | Gemini model | `gemini-3.5-flash-lite` |
| `FINREQ_GROQ_MODEL` | Groq model | `openai/gpt-oss-120b` |
| `FINREQ_OLLAMA_HOST` | Ollama endpoint | local Ollama |
| `FINREQ_DB_PATH` | SQLite database holding all analyses | `finreq.db` |
| `GEMINI_API_KEY`, `GROQ_API_KEY` | API credentials (environment only) | none |

Measured model comparisons and free-tier rate-limit behaviour are in
[ARCHITECTURE.md](ARCHITECTURE.md).

## Project layout

```
backend/
  finreq/            Python package
    agents/          one module per agent
    pipeline.py      orchestrator
    llm.py           Ollama, Gemini, Groq and fake clients
    sdlc.py          SDLC ranking engine
    retrieval.py     TF-IDF knowledge-base retrieval
    storage.py       SQLite persistence
    artifacts.py     document generation
  server.py          FastAPI app, serves the built front end
  cli.py             headless runner
  data/              sample policies and fixtures
  eval/, scripts/    benchmarks and delivery gates
  tests/             pytest suite (no model needed)
frontend/            React 19, Vite, Tailwind v4, shadcn/ui
docs/, guide/        SDLC record, code map, flowcharts, explainer
```

## Quality and verification

```bash
pip install -r backend/requirements-dev.txt
python -m pytest                         # backend tests, no model required
python backend/scripts/gates.py          # all delivery gates
python backend/eval/evaluate.py --live   # extraction quality vs. gold set (needs a model)
```

The delivery gates, also run in CI, cover tests, evaluation thresholds
(quality-check F1 ≥ 0.95, conflict accuracy ≥ 0.85), static analysis with
`bandit`, a secret scan, the front-end build with `npm audit`, and
`pip-audit`. Use `--skip-audit` to run offline.

## Security and governance

- **Human in the loop.** Only an explicit human action changes approval
  status. The compliance agent never makes a final legal determination.
- **Audit everything.** Every model call, retrieval, decision and sign-off is
  recorded.
- **PII masking** happens before any model call. Real values are restored only
  on human-facing fields.
- **Credentials** are read from the environment only. No flag, route or UI
  field accepts a key.
- **Offline retrieval.** Policy lookup uses local TF-IDF, with no external
  service.

Not implemented, as out of scope for a prototype: RBAC, MFA, encryption at
rest and session isolation.

## Limitations

- The sample policy knowledge base is fictional. Compliance output is not
  legal advice.
- Small local models can merge statements or omit justifications, which
  lowers recall. A larger model trades speed for coverage.
- TF-IDF duplicate detection misses paraphrases. Semantic embeddings would fix
  this.
- Free-tier API keys are rate limited. A full analysis can take minutes.

The full list is in [ARCHITECTURE.md](ARCHITECTURE.md#known-limitations-found-via-real-runs-not-hypothetical).

## Further reading

- [ARCHITECTURE.md](ARCHITECTURE.md): architecture, model measurements and constraints
- [DESIGN.md](DESIGN.md): the UI design system
- [docs/SDLC.md](docs/SDLC.md): how the project itself was built
- [guide/](guide/): code map, flowcharts and interactive explainer
