#!/usr/bin/env python
"""FinReq HTTP API + web front end.

    python backend/server.py          # http://127.0.0.1:8000 (serves frontend/dist if built)

The React app in frontend/ talks to these /api routes. Analyses run in a
background thread (a local model takes 1-4 minutes) and the client polls
GET /api/analyses/{id} for stage progress. Every analysis is saved to the
store, so GET /api/analyses (the front end's project list) survives a
restart. Everything else is a thin
wrapper over the same functions cli.py and the tests use.

The Gemini key is read from this process's environment only (see the README); no route accepts or returns it.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import threading
import time
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Callable, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from finreq import llm as llm_module
from finreq.agents.approval import (
    SDLC_APPROVER_ROLES, InvalidApprovalAction, record_decision, record_sdlc_signoff, sdlc_signoffs,
)
from finreq.artifacts import generate_all_artifacts
from finreq.config import SETTINGS
from finreq.models import AuditEvent, Requirement, RiskItem
from finreq.pipeline import run_pipeline
from finreq.retrieval import KnowledgeBase
from finreq.sdlc import DERIVED_FACTORS, FACTOR_LABELS, MODELS, derive_factors, rank, render_plan, workflow
from finreq.storage import Store

BACKEND = os.path.dirname(os.path.abspath(__file__))
REVIEWER_ROLES = ("business_analyst", "product_owner") + SDLC_APPROVER_ROLES
STAKEHOLDER_ROLES = ("loan_officer", "security_officer", "compliance_officer", "business_analyst",
                     "risk_manager", "operations_manager", "customer")
DECISIONS = ("accept", "reject", "modify", "regenerate")


def _read(rel: str) -> str:
    with open(os.path.join(BACKEND, rel), encoding="utf-8") as f:
        return f.read()


def _default_profile() -> dict[str, float]:
    return {k: v for k, v in json.loads(_read("data/fixtures/loan_project_profile.json")).items()
            if not k.startswith("_")}


@dataclass
class Analysis:
    id: str
    settings: dict
    transcript: str = ""
    status: str = "running"            # running | done | failed
    stages: list[str] = field(default_factory=list)
    error: Optional[str] = None
    started: float = field(default_factory=time.time)
    finished: Optional[float] = None
    elapsed: Optional[float] = None
    requirements: list[Requirement] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)
    questions: list[dict] = field(default_factory=list)
    factors: dict[str, float] = field(default_factory=dict)
    chosen: Optional[str] = None


# Saved as-is; requirements and risks are saved by id (they live in their own tables).
_SAVED = ("settings", "transcript", "status", "stages", "error", "started", "finished", "elapsed",
          "questions", "factors", "chosen")


class AnalysisRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=200_000)
    name: str = Field("", max_length=80)
    stakeholder_role: str = "loan_officer"
    domain_tag: str = Field("LOAN", pattern=r"^[A-Za-z0-9]{1,12}$")
    backend: str = Field(SETTINGS.llm_backend, pattern="^(ollama|gemini|groq)$")
    model: Optional[str] = Field(None, max_length=100)
    ask_clarifying_questions: bool = True


class DecisionRequest(BaseModel):
    action: str
    actor_role: str
    note: str = Field("", max_length=2000)
    statement: Optional[str] = Field(None, max_length=5000)


class ActorRequest(BaseModel):
    actor_role: str


class SDLCUpdate(BaseModel):
    factors: Optional[dict[str, float]] = None
    chosen: Optional[str] = None


class AppFiles(StaticFiles):
    """web/dist with cache headers. Vite's hashed assets never change, so they cache
    for a year; index.html (and the rest) must be revalidated every time, or a browser
    keeps running an old build after `npm run build`."""

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        hashed = path.replace("\\", "/").startswith("assets/")
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable" if hashed else "no-cache"
        return response


def _check_role(role: str) -> None:
    if role not in REVIEWER_ROLES:
        raise HTTPException(400, f"Unknown reviewer role '{role}'. Use one of: {', '.join(REVIEWER_ROLES)}.")


def create_app(store: Optional[Store] = None,
               llm_factory: Optional[Callable] = None) -> FastAPI:
    """`store`/`llm_factory` are injectable for tests; defaults are the
    SQLite file from config and finreq.llm.build_llm_client."""
    store = store or Store(SETTINGS.db_path)
    kb = KnowledgeBase()
    analyses: dict[str, Analysis] = {}
    app = FastAPI(title="FinReq", docs_url="/api/docs", openapi_url="/api/openapi.json")

    def _save(a: Analysis) -> None:
        store.save_analysis(a.id, a.started, {**{k: getattr(a, k) for k in _SAVED},
                                              "requirement_ids": [r.id for r in a.requirements],
                                              "risk_ids": [r.id for r in a.risks]})

    reqs = {r.id: r for r in store.all_requirements()}
    risks = {r.id: r for r in store.all_risks()}
    for saved in store.all_analyses():
        a = Analysis(id=saved["id"], **{k: saved[k] for k in _SAVED},
                     requirements=[reqs[i] for i in saved["requirement_ids"] if i in reqs],
                     risks=[risks[i] for i in saved["risk_ids"] if i in risks])
        if a.status == "running":      # its thread died with the previous server process
            a.status, a.error = "failed", "The server stopped before this analysis finished. Run it again."
            _save(a)
        analyses[a.id] = a

    def _get(analysis_id: str) -> Analysis:
        if analysis_id not in analyses:
            raise HTTPException(404, "No analysis with that id. Start a new one.")
        return analyses[analysis_id]

    def _done(analysis_id: str) -> Analysis:
        a = _get(analysis_id)
        if a.status != "done":
            raise HTTPException(409, "This analysis has not finished yet.")
        return a

    def _sdlc_view(a: Analysis) -> dict:
        ranking = rank(a.factors)
        chosen = a.chosen if a.chosen in MODELS else ranking[0].key
        signed = sdlc_signoffs(store, chosen, scope=a.id)
        return {
            "factors": a.factors,
            "labels": FACTOR_LABELS,
            "derived": list(DERIVED_FACTORS),
            "ranking": [asdict(s) for s in ranking],
            "recommended": ranking[0].key,
            "chosen": chosen,
            "workflow": [asdict(p) for p in workflow(chosen)],
            "approvers": list(SDLC_APPROVER_ROLES),
            "signed": sorted(signed),
            "baselined": set(SDLC_APPROVER_ROLES) <= signed,
        }

    def _view(a: Analysis) -> dict:
        body = {"id": a.id, "status": a.status, "stages": a.stages, "error": a.error,
                "settings": a.settings, "started": a.started,
                "elapsed": a.elapsed if a.elapsed is not None else round(time.time() - a.started, 1)}
        if a.status != "running":      # not while polling: the transcript can be 200 kB
            body["transcript"] = a.transcript
        if a.status == "done":
            body.update({
                "requirements": [req.model_dump(mode="json") for req in a.requirements],
                "risks": [risk.model_dump(mode="json") for risk in a.risks],
                "questions": a.questions,
                "sdlc": _sdlc_view(a),
            })
        return body

    def _run(a: Analysis, req: AnalysisRequest) -> None:
        try:
            factory = llm_factory or llm_module.build_llm_client
            result = run_pipeline(
                req.transcript, stakeholder_role=req.stakeholder_role, domain_tag=req.domain_tag.upper(),
                llm=factory(req.backend, req.model), kb=kb, store=store,
                ask_clarifying_questions=req.ask_clarifying_questions, on_stage=a.stages.append)
            a.factors = derive_factors(result.requirements, _default_profile())
            a.requirements, a.risks = result.requirements, result.risks
            a.questions = [q.model_dump() for q in result.clarification.questions]
            a.status = "done"
        except Exception as exc:  # noqa: BLE001 — surfaced to the reviewer as a readable message
            a.error = f"{exc}" if isinstance(exc, (llm_module.LLMError, ValueError)) else (
                f"{type(exc).__name__}: {exc}. With Ollama, check it is running (`ollama serve`) "
                f"and the model is pulled.")
            a.status = "failed"
        finally:
            a.finished = time.time()
            a.elapsed = round(a.finished - a.started, 1)
            _save(a)

    @app.get("/api/config")
    def config() -> dict:
        return {
            "backends": {"ollama": SETTINGS.model, "gemini": SETTINGS.gemini_model,
                         "groq": SETTINGS.groq_model},
            "default_backend": SETTINGS.llm_backend,
            "gemini_key_set": bool(os.environ.get(SETTINGS.gemini_api_key_env)),
            "gemini_key_env": SETTINGS.gemini_api_key_env,
            "groq_key_set": bool(os.environ.get(SETTINGS.groq_api_key_env)),
            "groq_key_env": SETTINGS.groq_api_key_env,
            "reviewer_roles": list(REVIEWER_ROLES),
            "stakeholder_roles": list(STAKEHOLDER_ROLES),
            "sample_transcript": _read("data/fixtures/loan_officer_interview.txt"),
        }

    @app.get("/api/groq/models")
    def groq_models() -> list[dict]:
        """Groq's chat models for the model picker (fetched with the server's key;
        only ids reach the browser)."""
        return llm_module.groq_models()

    @app.get("/api/ollama/models")
    def ollama_models() -> list[dict]:
        """Models pulled into the local Ollama server, for the model picker."""
        return llm_module.ollama_models()

    @app.post("/api/analyses", status_code=202)
    def start(req: AnalysisRequest) -> dict:
        if not req.transcript.strip():
            raise HTTPException(400, "The transcript is empty. Paste or load one first.")
        if req.stakeholder_role not in STAKEHOLDER_ROLES:
            raise HTTPException(400, f"Unknown stakeholder role '{req.stakeholder_role}'.")
        settings = req.model_dump(exclude={"transcript"})
        settings["name"] = req.name.strip() or f"{req.stakeholder_role.replace('_', ' ').capitalize()} interview"
        a = Analysis(id=uuid.uuid4().hex[:12], settings=settings, transcript=req.transcript)
        analyses[a.id] = a
        _save(a)
        threading.Thread(target=_run, args=(a, req), daemon=True).start()
        return {"id": a.id}

    @app.get("/api/analyses")
    def projects() -> list[dict]:
        """Every analysis, newest first, summarised for the project list."""
        rows = []
        for a in sorted(analyses.values(), key=lambda a: a.started, reverse=True):
            statuses = [r.approval_status.value for r in a.requirements]
            row = {"id": a.id, "name": a.settings["name"], "status": a.status, "started": a.started,
                   "requirements": len(statuses),
                   "decided": statuses.count("approved") + statuses.count("rejected"), "sdlc": None}
            if a.status == "done":
                sdlc = _sdlc_view(a)
                row["sdlc"] = {"name": MODELS[sdlc["chosen"]][0], "signed": len(sdlc["signed"]),
                               "approvers": len(sdlc["approvers"]), "baselined": sdlc["baselined"]}
            rows.append(row)
        return rows

    @app.get("/api/analyses/{analysis_id}")
    def get(analysis_id: str) -> dict:
        return _view(_get(analysis_id))

    @app.delete("/api/analyses/{analysis_id}", status_code=204)
    def delete(analysis_id: str) -> Response:
        a = _get(analysis_id)
        if a.status == "running":
            raise HTTPException(409, "This analysis is still running. Delete it once it has finished.")
        del analyses[analysis_id]
        store.delete_analysis(analysis_id)
        store.log_event(AuditEvent(agent="server", event_type="deletion",
                                   payload=json.dumps({"analysis": analysis_id, "name": a.settings["name"]})))
        return Response(status_code=204)

    @app.post("/api/analyses/{analysis_id}/requirements/{req_id}/decision")
    def decide(analysis_id: str, req_id: str, body: DecisionRequest) -> dict:
        a = _done(analysis_id)
        _check_role(body.actor_role)
        if body.action not in DECISIONS:
            raise HTTPException(400, f"Unknown decision '{body.action}'.")
        req = next((r for r in a.requirements if r.id == req_id), None)
        if req is None:
            raise HTTPException(404, f"{req_id} is not part of this analysis.")
        if body.action == "modify":
            text = (body.statement or "").strip()
            if not text:
                raise HTTPException(400, "An edit needs the new requirement text.")
            req.statement = text
        record_decision(store, req, body.action, body.actor_role, body.note or
                        ("edited by reviewer" if body.action == "modify" else ""))
        return _view(a)

    @app.post("/api/analyses/{analysis_id}/bulk-accept")
    def bulk_accept(analysis_id: str, body: ActorRequest) -> dict:
        a = _done(analysis_id)
        _check_role(body.actor_role)
        for r in a.requirements:
            if (r.approval_status.value == "pending_review" and not r.quality_issues
                    and not r.conflicts_with and not r.duplicate_of):
                record_decision(store, r, "accept", body.actor_role, "bulk-accepted: no open issues")
        return _view(a)

    @app.put("/api/analyses/{analysis_id}/sdlc")
    def update_sdlc(analysis_id: str, body: SDLCUpdate) -> dict:
        a = _done(analysis_id)
        if body.factors:
            try:
                a.factors = derive_factors([], {**a.factors, **body.factors})
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from None
        if body.chosen is not None:
            if body.chosen not in MODELS:
                raise HTTPException(400, f"Unknown SDLC model '{body.chosen}'.")
            a.chosen = body.chosen
        _save(a)
        return _view(a)

    @app.post("/api/analyses/{analysis_id}/sdlc/signoff")
    def signoff(analysis_id: str, body: ActorRequest) -> dict:
        a = _done(analysis_id)
        try:
            record_sdlc_signoff(store, _sdlc_view(a)["chosen"], body.actor_role, scope=a.id)
        except InvalidApprovalAction as exc:
            raise HTTPException(403, str(exc)) from None
        return _view(a)

    @app.get("/api/analyses/{analysis_id}/export")
    def export(analysis_id: str) -> Response:
        a = _done(analysis_id)
        view = _sdlc_view(a)
        plan = render_plan(rank(a.factors), view["chosen"], a.factors, set(view["signed"]), SDLC_APPROVER_ROLES)
        buf = io.BytesIO()
        with tempfile.TemporaryDirectory() as tmp:
            paths = generate_all_artifacts(a.requirements, a.risks, tmp,
                                           project_name=a.settings["domain_tag"], sdlc_plan=plan)
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for name, path in paths.items():
                    z.write(path, name)
        return Response(buf.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="prism-{a.id}.zip"'})

    @app.get("/api/audit")
    def audit(analysis: Optional[str] = None) -> dict:
        events, decisions = store.all_events(), store.approvals_all()
        if analysis is not None:
            a = _get(analysis)
            # ponytail: a time window, so overlapping concurrent runs would share events;
            # tag each AuditEvent with its analysis id if that ever matters.
            end = a.finished or time.time()
            events = [e for e in events if a.started <= datetime.fromisoformat(e.timestamp).timestamp() <= end]
            ids = {r.id for r in a.requirements}
            decisions = [d for d in decisions if d.target_id in ids or d.target_id.startswith(f"{a.id}:")]
        return {"events": [e.model_dump() for e in events][-500:],
                "decisions": [d.model_dump() for d in decisions]}

    dist = os.path.join(BACKEND, "..", "frontend", "dist")
    if os.path.isdir(dist):
        app.mount("/", AppFiles(directory=dist, html=True), name="web")
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=int(os.environ.get("FINREQ_PORT", "8000")))
