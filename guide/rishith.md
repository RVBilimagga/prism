# Prism · Code map

> Every file and function in FinReq, one click away. Start at the top, follow the tour.

**Legend** (Kind column on agents): **LLM** = calls a language model. **rule** = pure Python, deterministic and explainable for audit. **human** = records a person's decision.

Line links use `#L<n>`, which works in the VS Code markdown preview and on GitHub. Paths are relative to this `guide/` folder.

---

## Start here

| Link | What it does |
|---|---|
| [ARCHITECTURE.md](../ARCHITECTURE.md) | Commands, architecture and constraints for working in this repo |
| [README.md](../README.md) | Project overview and how to run the app |
| [DESIGN.md](../DESIGN.md) | Prism design system: tokens, themes, flow, motion |
| [pipeline.py:59 — run_pipeline](../backend/finreq/pipeline.py#L59) | The orchestrator. Every agent runs from here, in order |
| [server.py:130 — create_app](../backend/server.py#L130) | Builds the FastAPI app that serves `/api` and the React build |
| [frontend/src/App.tsx:41 — App](../frontend/src/App.tsx#L41) | React state machine: start, run, failed, steps |
| [cli.py:34 — main](../backend/cli.py#L34) | Headless run from the terminal |
| [flowchart.md](./flowchart.md) | The same system as Mermaid diagrams |
| [index.html](./index.html) | Interactive project explainer (open in a browser) |

## Orchestrator

| Link | What it does |
|---|---|
| [pipeline.py:40 — PipelineResult](../backend/finreq/pipeline.py#L40) | Return value: requirements, risks, clarification, masking |
| [pipeline.py:48 — _unmask_requirement](../backend/finreq/pipeline.py#L48) | Restores real values into human-facing fields only, after all LLM calls |
| [pipeline.py:94 — AgentContext built](../backend/finreq/pipeline.py#L94) | One shared context (llm, kb, store, audit log) for all agents |
| [pipeline.py:97 — mask_text](../backend/finreq/pipeline.py#L97) | Masks PII once, at ingestion. LLM agents only see masked text |
| [pipeline.py:106 — interaction](../backend/finreq/pipeline.py#L106) | Optional clarifying questions for the stakeholder |
| [pipeline.py:109 — extraction](../backend/finreq/pipeline.py#L109) | Turns the transcript into requirements |
| [pipeline.py:114 — classification](../backend/finreq/pipeline.py#L114) | Multi-label categories per requirement |
| [pipeline.py:117 — quality](../backend/finreq/pipeline.py#L117) | Ambiguity, completeness, testability checks |
| [pipeline.py:120 — conflict](../backend/finreq/pipeline.py#L120) | Duplicates and contradictions |
| [pipeline.py:123 — compliance](../backend/finreq/pipeline.py#L123) | Maps each requirement to policy evidence |
| [pipeline.py:128 — security](../backend/finreq/pipeline.py#L128) | Security and privacy tagging, missing-control check |
| [pipeline.py:131 — risk](../backend/finreq/pipeline.py#L131) | Risk scores and risk level per requirement |
| [pipeline.py:134 — validation](../backend/finreq/pipeline.py#L134) | Routes each requirement to clarification or review |
| [pipeline.py:136 — unmask and save](../backend/finreq/pipeline.py#L136) | Restores values, then writes requirements and risks to the store |

## LLM backends

| Link | What it does |
|---|---|
| [llm.py:25 — LLMError](../backend/finreq/llm.py#L25) | Error type. Carries the provider message, never the key |
| [llm.py:29 — LLMClient](../backend/finreq/llm.py#L29) | Abstract base for every backend |
| [llm.py:36 — generate_json](../backend/finreq/llm.py#L36) | JSON output with repair retries |
| [llm.py:61 — unwrap_single](../backend/finreq/llm.py#L61) | Undoes a small model wrapping one object in a 1-item array |
| [llm.py:69 — _extract_json](../backend/finreq/llm.py#L69) | Pulls the JSON object out of raw model text |
| [llm.py:98 — OllamaClient](../backend/finreq/llm.py#L98) | Local backend, default `qwen2.5:3b-instruct` |
| [llm.py:128 — GeminiClient](../backend/finreq/llm.py#L128) | Gemini API. Key from `GEMINI_API_KEY` only, sent as a header |
| [llm.py:210 — _retry_after](../backend/finreq/llm.py#L210) | Reads retry delays for rate limits and overload |
| [llm.py:225 — GroqClient](../backend/finreq/llm.py#L225) | Groq OpenAI-compatible API. Key from `GROQ_API_KEY` only |
| [llm.py:301 — groq_models](../backend/finreq/llm.py#L301) | Model list for the UI dropdown, cached an hour |
| [llm.py:325 — ollama_models](../backend/finreq/llm.py#L325) | Models pulled into local Ollama, for the model picker |
| [llm.py:338 — build_llm_client](../backend/finreq/llm.py#L338) | Single entry point that picks a backend |
| [llm.py:351 — FakeLLMClient](../backend/finreq/llm.py#L351) | Scripted client for tests (no Ollama needed) |
| [config.py:11 — load_dotenv](../backend/finreq/config.py#L11) | Copies `.env` into the environment. A shell value wins |
| [config.py:28 — Settings](../backend/finreq/config.py#L28) | All settings in one place: model, thresholds, DB path |

## Agents

| Link | What it does | Kind |
|---|---|---|
| [agents/base.py:25 — AgentContext](../backend/finreq/agents/base.py#L25) | Shared llm, kb, store and audit log | base |
| [agents/base.py:36 — Agent](../backend/finreq/agents/base.py#L36) | Base class; `call_llm_json` logs every model call | base |
| [agents/interaction.py:52 — StakeholderInteractionAgent](../backend/finreq/agents/interaction.py#L52) | Asks clarifying questions over topic areas | **LLM** |
| [agents/extraction.py:33 — ExtractionAgent](../backend/finreq/agents/extraction.py#L33) | Extracts requirements from masked transcript | **LLM** |
| [agents/classification.py:20 — ClassificationAgent](../backend/finreq/agents/classification.py#L20) | Multi-label requirement categories | **LLM** |
| [agents/quality.py:46 — QualityCheckAgent](../backend/finreq/agents/quality.py#L46) | Vague terms, missing modal verbs, infeasible wording | **rule** |
| [agents/conflict.py:29 — _looks_contradictory](../backend/finreq/agents/conflict.py#L29) | Negation test for contradictions | **rule** |
| [agents/conflict.py:40 — ConflictDetectionAgent](../backend/finreq/agents/conflict.py#L40) | TF-IDF duplicates and contradictions | **rule** |
| [agents/compliance.py:26 — ComplianceAgent](../backend/finreq/agents/compliance.py#L26) | Retrieval-grounded policy mapping; low confidence = gap | **LLM** |
| [agents/security.py:29 — SecurityPrivacyAgent](../backend/finreq/agents/security.py#L29) | Security and privacy tagging, missing controls | **rule** |
| [agents/risk.py:63 — assess](../backend/finreq/agents/risk.py#L63) | Scores one requirement into a risk item | **rule** |
| [agents/risk.py:101 — RiskAnalysisAgent](../backend/finreq/agents/risk.py#L101) | Sets `requirement.risk_level` from the same score | **rule** |
| [agents/validation.py:30 — ValidationAgent](../backend/finreq/agents/validation.py#L30) | Clarification vs pending review | **rule** |
| [agents/approval.py:33 — record_decision](../backend/finreq/agents/approval.py#L33) | The only place human decisions change approval status | **human** |
| [agents/approval.py:70 — record_sdlc_signoff](../backend/finreq/agents/approval.py#L70) | Records one of the four SDLC sign-offs | **human** |
| [agents/approval.py:85 — sdlc_signoffs](../backend/finreq/agents/approval.py#L85) | Which sign-offs a model already has |  **human** |

## Data and storage

| Link | What it does |
|---|---|
| [models.py:21 — RequirementCategory](../backend/finreq/models.py#L21) | Requirement category enum |
| [models.py:51 — ApprovalStatus](../backend/finreq/models.py#L51) | Approval states: draft, needs_clarification, pending_review, approved, rejected, needs_regeneration |
| [models.py:79 — Evidence](../backend/finreq/models.py#L79) | One retrieved policy excerpt, with score |
| [models.py:92 — ComplianceMapping](../backend/finreq/models.py#L92) | Requirement-to-policy mapping and gap flag |
| [models.py:101 — Requirement](../backend/finreq/models.py#L101) | The core record: statement, quality issues, status, risk |
| [models.py:130 — RiskItem](../backend/finreq/models.py#L130) | One row of the risk register |
| [models.py:141 — ApprovalRecord](../backend/finreq/models.py#L141) | One human decision or sign-off |
| [models.py:152 — AuditEvent](../backend/finreq/models.py#L152) | One logged step (model call, retrieval, decision) |
| [masking.py:32 — MaskingResult](../backend/finreq/masking.py#L32) | Masked text plus the mapping to unmask it |
| [masking.py:42 — mask_text](../backend/finreq/masking.py#L42) | Regex PII masking: emails, cards, PAN, IFSC, phone, account no. |
| [retrieval.py:50 — _parse_document](../backend/finreq/retrieval.py#L50) | Reads a policy file and its provenance header |
| [retrieval.py:88 — KnowledgeBase](../backend/finreq/retrieval.py#L88) | TF-IDF and cosine retrieval over the policy folder |
| [storage.py:45 — Store](../backend/finreq/storage.py#L45) | SQLite store: requirements, risks, approvals, analyses, audit |
| [storage.py:151 — in_memory_store](../backend/finreq/storage.py#L151) | In-memory store for tests and one-off runs |

## SDLC engine

| Link | What it does |
|---|---|
| [sdlc.py:20 — FACTOR_LABELS](../backend/finreq/sdlc.py#L20) | The 13 factors the ranking uses |
| [sdlc.py:67 — SDLCScore](../backend/finreq/sdlc.py#L67) | One model's score with its reasons |
| [sdlc.py:75 — derive_factors](../backend/finreq/sdlc.py#L75) | 4 factors from requirements, the rest from the project profile |
| [sdlc.py:111 — rank](../backend/finreq/sdlc.py#L111) | Weighted MCDA. Sorts on the unrounded score |
| [sdlc.py:129 — Phase](../backend/finreq/sdlc.py#L129) | One workflow phase |
| [sdlc.py:204 — workflow](../backend/finreq/sdlc.py#L204) | Phases for a chosen model, with financial controls built in |
| [sdlc.py:208 — render_plan](../backend/finreq/sdlc.py#L208) | Markdown SDLC plan |
| [agents/approval.py:19 — SDLC_APPROVER_ROLES](../backend/finreq/agents/approval.py#L19) | The four roles that must sign off |

## Artefacts

| Link | What it does |
|---|---|
| [artifacts.py:91 — render_user_stories](../backend/finreq/artifacts.py#L91) | `user_stories.md` |
| [artifacts.py:150 — render_srs](../backend/finreq/artifacts.py#L150) | `SRS.md` |
| [artifacts.py:180 — generate_all_artifacts](../backend/finreq/artifacts.py#L180) | Writes every CSV and Markdown artefact |

## API server

| Link | What it does |
|---|---|
| [server.py:65 — Analysis](../backend/server.py#L65) | In-memory run state: stages, status, decisions |
| [server.py:113 — AppFiles](../backend/server.py#L113) | Serves `frontend/dist`; hashed assets cached forever, `index.html` never cached |
| [server.py:130 — create_app](../backend/server.py#L130) | App factory, injectable store and LLM for tests |
| [server.py:219 — GET /api/config](../backend/server.py#L219) | Roles, backends, defaults for the UI |
| [server.py:234 — GET /api/groq/models](../backend/server.py#L234) | Groq model dropdown |
| [server.py:240 — GET /api/ollama/models](../backend/server.py#L240) | Models pulled into local Ollama, for the model picker |
| [server.py:245 — POST /api/analyses](../backend/server.py#L245) | Starts a run, returns 202 |
| [server.py:259 — GET /api/analyses](../backend/server.py#L259) | Project list |
| [server.py:275 — GET /api/analyses/id](../backend/server.py#L275) | One analysis, polled for stage progress |
| [server.py:279 — DELETE /api/analyses/id](../backend/server.py#L279) | Removes the project, keeps audit events |
| [server.py:290 — decision](../backend/server.py#L290) | Accept, reject, modify or regenerate one requirement |
| [server.py:308 — bulk-accept](../backend/server.py#L308) | Accepts every pending requirement |
| [server.py:318 — PUT sdlc](../backend/server.py#L318) | Saves the factor sliders and the chosen model |
| [server.py:333 — signoff](../backend/server.py#L333) | Records one SDLC sign-off |
| [server.py:342 — export](../backend/server.py#L342) | Downloads the artefacts |
| [server.py:357 — audit](../backend/server.py#L357) | Audit trail, scoped to a project or all |

## CLI

| Link | What it does |
|---|---|
| [cli.py:34 — main](../backend/cli.py#L34) | Headless run: stage progress, requirements, top 3 SDLC models |
| [cli.py:71 — _on_stage](../backend/cli.py#L71) | Prints each stage as it starts |

## Web UI (React)

| Link | What it does |
|---|---|
| [frontend/src/App.tsx:41 — App](../frontend/src/App.tsx#L41) | State machine, polling, `?analysis=` URL state |
| [frontend/src/lib/api.ts:64 — api](../frontend/src/lib/api.ts#L64) | Typed calls to `/api` |
| [frontend/src/components/TopBar.tsx:15 — TopBar](../frontend/src/components/TopBar.tsx#L15) | Brand, projects, audit, theme toggle, reviewer |
| [frontend/src/components/StepRail.tsx:6 — Step](../frontend/src/components/StepRail.tsx#L6) | Step type: transcript, review, delivery, export |
| [frontend/src/components/StepRail.tsx:7 — STEPS](../frontend/src/components/StepRail.tsx#L7) | The step rail and its icons |
| [frontend/src/components/Hero.tsx:35 — StartHero](../frontend/src/components/Hero.tsx#L35) | Start screen headline and calls to action |
| [frontend/src/components/InputPanel.tsx:28 — InputPanel](../frontend/src/components/InputPanel.tsx#L28) | The transcript composer and backend picker |
| [frontend/src/components/RunView.tsx:11 — PLANNED_STAGES](../frontend/src/components/RunView.tsx#L11) | Stage labels. Must match `pipeline.py` |
| [frontend/src/components/RunView.tsx:34 — RunView](../frontend/src/components/RunView.tsx#L34) | The live run screen |
| [frontend/src/components/ProjectsList.tsx:91 — ProjectsList](../frontend/src/components/ProjectsList.tsx#L91) | The five newest projects under the composer |
| [frontend/src/components/ProjectsList.tsx:118 — ProjectsSheet](../frontend/src/components/ProjectsList.tsx#L118) | All projects, plus new analysis |
| [frontend/src/components/review/ReviewStep.tsx:29 — ReviewStep](../frontend/src/components/review/ReviewStep.tsx#L29) | Filters, keyboard review, inspector |
| [frontend/src/components/review/RequirementList.tsx:22 — RequirementList](../frontend/src/components/review/RequirementList.tsx#L22) | Filterable requirement list |
| [frontend/src/components/review/Inspector.tsx:34 — Inspector](../frontend/src/components/review/Inspector.tsx#L34) | Evidence trace and decision bar |
| [frontend/src/components/review/RiskMap.tsx:18 — RiskMap](../frontend/src/components/review/RiskMap.tsx#L18) | Likelihood by impact grid |
| [frontend/src/components/review/QuestionsSheet.tsx:16 — QuestionsSheet](../frontend/src/components/review/QuestionsSheet.tsx#L16) | Clarifying questions panel |
| [frontend/src/components/DeliveryStep.tsx:23 — DeliveryStep](../frontend/src/components/DeliveryStep.tsx#L23) | SDLC factors, ranking, workflow, sign-offs |
| [frontend/src/components/ExportStep.tsx:27 — ExportStep](../frontend/src/components/ExportStep.tsx#L27) | Download list for the artefacts |
| [frontend/src/components/AuditSheet.tsx:25 — AuditSheet](../frontend/src/components/AuditSheet.tsx#L25) | Audit events, scoped to the open project |
| [frontend/src/components/kit.tsx:11 — shared primitives](../frontend/src/components/kit.tsx#L11) | IconTile, PanelHeader, ProgressRing and friends |
| [frontend/src/components/pills.tsx:10 — TONE](../frontend/src/components/pills.tsx#L10) | Tone palette and status and risk pills |
| [frontend/src/components/Logo.tsx:3 — BRAND](../frontend/src/components/Logo.tsx#L3) | The brand name, Prism |
| [frontend/src/index.css:11 — tokens](../frontend/src/index.css#L11) | Every colour token, light and dark |

## Quality gates and eval

| Link | What it does |
|---|---|
| [scripts/gates.py:37 — gate_tests](../backend/scripts/gates.py#L37) | Runs pytest |
| [scripts/gates.py:41 — gate_eval](../backend/scripts/gates.py#L41) | Runs the eval thresholds |
| [scripts/gates.py:52 — gate_sast](../backend/scripts/gates.py#L52) | Bandit static analysis |
| [scripts/gates.py:59 — gate_web](../backend/scripts/gates.py#L59) | Web build and npm audit |
| [scripts/gates.py:77 — gate_secrets](../backend/scripts/gates.py#L77) | Secret-pattern scan over tracked files |
| [scripts/gates.py:93 — main](../backend/scripts/gates.py#L93) | Runs every gate |
| [eval/evaluate.py:58 — run_quality_benchmark](../backend/eval/evaluate.py#L58) | Quality-check F1 benchmark |
| [eval/evaluate.py:86 — run_conflict_benchmark](../backend/eval/evaluate.py#L86) | Conflict-detection benchmark |
| [eval/evaluate.py:118 — run_live_extraction_eval](../backend/eval/evaluate.py#L118) | Live extraction eval against a real model |
| [eval/evaluate.py:176 — main](../backend/eval/evaluate.py#L176) | Eval entry point |

## Tests

| Link | What it does |
|---|---|
| [tests/test_pipeline_integration.py](../backend/tests/test_pipeline_integration.py) | End-to-end pipeline with the fake LLM |
| [tests/test_api.py](../backend/tests/test_api.py) | FastAPI routes via TestClient |
| [tests/test_llm.py](../backend/tests/test_llm.py) | JSON repair and `unwrap_single` |
| [tests/test_gemini_client.py](../backend/tests/test_gemini_client.py) | Gemini request shape and missing-key path |
| [tests/test_groq_client.py](../backend/tests/test_groq_client.py) | Groq request shape and retry handling |
| [tests/test_quality.py](../backend/tests/test_quality.py) | Quality-check rules |
| [tests/test_conflict.py](../backend/tests/test_conflict.py) | Duplicate and contradiction detection |
| [tests/test_compliance.py](../backend/tests/test_compliance.py) | Policy mapping and gap flags |
| [tests/test_security.py](../backend/tests/test_security.py) | Security and privacy tagging |
| [tests/test_risk.py](../backend/tests/test_risk.py) | Risk scoring |
| [tests/test_validation_and_approval.py](../backend/tests/test_validation_and_approval.py) | Routing and human decisions |
| [tests/test_sdlc.py](../backend/tests/test_sdlc.py) | Factors, ranking and workflow |
| [tests/test_masking.py](../backend/tests/test_masking.py) | PII masking and unmasking |
| [tests/test_retrieval.py](../backend/tests/test_retrieval.py) | Knowledge-base retrieval |
| [tests/test_storage.py](../backend/tests/test_storage.py) | SQLite store round trips |
| [tests/test_artifacts.py](../backend/tests/test_artifacts.py) | Generated artefacts |
| [tests/test_gates.py](../backend/tests/test_gates.py) | The gate script itself |

## Docs and data

| Link | What it does |
|---|---|
| [docs/SDLC.md](../docs/SDLC.md) | How FinReq itself was built: model choice, sprints, gates, threats |
| [docs/finreq_self_analysis/](../docs/finreq_self_analysis/) | FinReq's analysis of its own problem statement |
| [data/knowledge_base/](../backend/data/knowledge_base/) | Five fictional sample policies (KYC, privacy, audit, transactions, credit fairness) |
| [data/knowledge_base/kyc_onboarding_policy.md](../backend/data/knowledge_base/kyc_onboarding_policy.md) | KYC and onboarding policy |
| [data/knowledge_base/data_privacy_consent_policy.md](../backend/data/knowledge_base/data_privacy_consent_policy.md) | Data privacy and consent policy |
| [data/knowledge_base/audit_reporting_policy.md](../backend/data/knowledge_base/audit_reporting_policy.md) | Audit and reporting policy |
| [data/knowledge_base/transaction_security_policy.md](../backend/data/knowledge_base/transaction_security_policy.md) | Transaction security policy |
| [data/knowledge_base/credit_decisioning_fairness_policy.md](../backend/data/knowledge_base/credit_decisioning_fairness_policy.md) | Credit decisioning and fairness policy |
| [data/fixtures/loan_officer_interview.txt](../backend/data/fixtures/loan_officer_interview.txt) | Sample stakeholder transcript used by the CLI and tests |
| [data/fixtures/problem_statement.txt](../backend/data/fixtures/problem_statement.txt) | Text copy of the problem statement |
| [eval/gold_requirements.json](../backend/eval/gold_requirements.json) | Gold requirements the live eval scores against |
| [ARCHITECTURE.md](../ARCHITECTURE.md) | Project instructions |
| [DESIGN.md](../DESIGN.md) | Front-end design system |
