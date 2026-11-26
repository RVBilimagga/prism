"""HTTP API tests (server.py) with FastAPI's TestClient and the scripted fake model."""
import io
import threading
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from finreq.llm import FakeLLMClient
from finreq.storage import in_memory_store
from test_pipeline_integration import _responder

import server

TRANSCRIPT = "We need extra verification for big transfers. Customers should get an SMS."


@pytest.fixture
def client():
    app = server.create_app(store=in_memory_store(),
                            llm_factory=lambda backend, model: FakeLLMClient(responder=_responder))
    return TestClient(app)


def _analyse(client, **overrides) -> dict:
    body = {"transcript": TRANSCRIPT, "stakeholder_role": "security_officer", **overrides}
    started = client.post("/api/analyses", json=body)
    assert started.status_code == 202, started.text
    for _ in range(200):
        view = client.get(f"/api/analyses/{started.json()['id']}").json()
        if view["status"] != "running":
            return view
        time.sleep(0.05)
    raise AssertionError("analysis did not finish")


def test_config_never_exposes_a_key(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder-not-a-real-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-placeholder-not-a-real-key")
    body = client.get("/api/config").json()
    assert body["gemini_key_set"] is True and body["groq_key_set"] is True
    assert body["backends"]["groq"] == "openai/gpt-oss-120b"
    assert "test-placeholder" not in str(body)
    assert "project_manager" in body["reviewer_roles"]


def test_analysis_runs_and_reports_stages_requirements_and_sdlc(client):
    view = _analyse(client)
    assert view["status"] == "done"
    assert any("Extracting" in s for s in view["stages"])
    assert [r["id"] for r in view["requirements"]] == ["FR-LOAN-001", "FR-LOAN-002"]
    assert len(view["risks"]) == 2
    sdlc = view["sdlc"]
    assert sdlc["chosen"] == sdlc["recommended"] == sdlc["ranking"][0]["key"]
    assert sdlc["baselined"] is False and len(sdlc["workflow"]) >= 3


def test_decisions_including_edit(client):
    view = _analyse(client)
    url = f"/api/analyses/{view['id']}/requirements/FR-LOAN-001/decision"
    accepted = client.post(url, json={"action": "accept", "actor_role": "product_owner"}).json()
    assert accepted["requirements"][0]["approval_status"] == "approved"
    edited = client.post(url, json={"action": "modify", "actor_role": "business_analyst",
                                    "statement": "The system shall require a second factor."}).json()
    first = edited["requirements"][0]
    assert first["statement"] == "The system shall require a second factor."
    assert first["approval_status"] == "pending_review"
    assert client.post(url, json={"action": "modify", "actor_role": "business_analyst"}).status_code == 400
    assert client.post(url, json={"action": "accept", "actor_role": "intern"}).status_code == 400
    assert client.post(url, json={"action": "approve_all", "actor_role": "product_owner"}).status_code == 400


def test_bulk_accept_only_takes_issue_free_pending(client):
    view = _analyse(client)
    after = client.post(f"/api/analyses/{view['id']}/bulk-accept", json={"actor_role": "product_owner"}).json()
    statuses = {r["id"]: r["approval_status"] for r in after["requirements"]}
    assert statuses == {"FR-LOAN-001": "approved", "FR-LOAN-002": "needs_clarification"}


def test_sdlc_update_and_four_signoffs(client):
    view = _analyse(client)
    base = f"/api/analyses/{view['id']}/sdlc"
    updated = client.put(base, json={"factors": {"change_frequency": 1.0}, "chosen": "agile_v_model"}).json()
    assert updated["sdlc"]["chosen"] == "agile_v_model"
    assert updated["sdlc"]["factors"]["change_frequency"] == 1.0
    assert client.put(base, json={"factors": {"budget": 1}}).status_code == 400
    assert client.put(base, json={"chosen": "scrumfall"}).status_code == 400
    assert client.post(base + "/signoff", json={"actor_role": "business_analyst"}).status_code == 403
    for role in ("project_manager", "architect", "security_lead", "compliance_officer"):
        last = client.post(base + "/signoff", json={"actor_role": role}).json()
    assert last["sdlc"]["baselined"] is True


def test_export_zip_contains_every_artefact(client):
    view = _analyse(client)
    resp = client.get(f"/api/analyses/{view['id']}/export")
    assert resp.status_code == 200 and resp.headers["content-type"] == "application/zip"
    names = set(zipfile.ZipFile(io.BytesIO(resp.content)).namelist())
    assert {"SRS.md", "sdlc_plan.md", "traceability_matrix.csv", "risk_register.csv"} <= names


def test_failures_are_readable(client):
    assert client.post("/api/analyses", json={"transcript": "   "}).status_code == 400
    assert client.post("/api/analyses", json={"transcript": "x", "domain_tag": "../etc"}).status_code == 422
    assert client.get("/api/analyses/nope").status_code == 404
    view = _analyse(client)
    assert client.get("/api/audit").json()["events"]
    assert client.get(f"/api/analyses/{view['id']}/export").status_code == 200


def test_model_failure_is_reported_not_raised():
    def broken(backend, model):
        raise server.llm_module.LLMError("GEMINI_API_KEY is not set.")
    app = server.create_app(store=in_memory_store(), llm_factory=broken)
    view = _analyse(TestClient(app))
    assert view["status"] == "failed" and "GEMINI_API_KEY" in view["error"]


def test_signoffs_do_not_leak_between_analyses(client):
    first = _analyse(client)
    for role in ("project_manager", "architect", "security_lead", "compliance_officer"):
        client.post(f"/api/analyses/{first['id']}/sdlc/signoff", json={"actor_role": role})
    second = _analyse(client)
    assert second["sdlc"]["chosen"] == first["sdlc"]["chosen"]
    assert second["sdlc"]["signed"] == [] and second["sdlc"]["baselined"] is False


def test_projects_survive_a_restart_newest_first():
    store = in_memory_store()
    factory = lambda backend, model: FakeLLMClient(responder=_responder)  # noqa: E731
    before = TestClient(server.create_app(store=store, llm_factory=factory))
    first = _analyse(before, name="Mortgage portal")
    second = _analyse(before, stakeholder_role="loan_officer")
    before.post(f"/api/analyses/{first['id']}/requirements/FR-LOAN-001/decision",
                json={"action": "accept", "actor_role": "product_owner"})
    before.put(f"/api/analyses/{first['id']}/sdlc", json={"chosen": "v_model"})

    after = TestClient(server.create_app(store=store, llm_factory=factory))
    projects = after.get("/api/analyses").json()
    assert [p["name"] for p in projects] == ["Loan officer interview", "Mortgage portal"]
    assert projects[1]["requirements"] == 2 and projects[1]["decided"] == 1
    assert projects[1]["sdlc"] == {"name": "V-Model", "signed": 0, "approvers": 4, "baselined": False}
    reopened = after.get(f"/api/analyses/{first['id']}").json()
    assert reopened["transcript"] == TRANSCRIPT and reopened["sdlc"]["chosen"] == "v_model"
    assert reopened["requirements"][0]["approval_status"] == "approved"
    assert after.get(f"/api/analyses/{second['id']}/export").status_code == 200


def test_deleting_a_project_removes_it_but_keeps_the_audit_trail():
    store = in_memory_store()
    factory = lambda backend, model: FakeLLMClient(responder=_responder)  # noqa: E731
    client = TestClient(server.create_app(store=store, llm_factory=factory))
    gone, kept = _analyse(client, name="Old"), _analyse(client, name="Kept")
    client.post(f"/api/analyses/{gone['id']}/requirements/FR-LOAN-001/decision",
                json={"action": "accept", "actor_role": "product_owner"})

    assert client.delete(f"/api/analyses/{gone['id']}").status_code == 204
    assert client.get(f"/api/analyses/{gone['id']}").status_code == 404
    assert client.delete(f"/api/analyses/{gone['id']}").status_code == 404
    assert [p["name"] for p in client.get("/api/analyses").json()] == ["Kept"]
    after = TestClient(server.create_app(store=store, llm_factory=factory))
    assert [p["id"] for p in after.get("/api/analyses").json()] == [kept["id"]]
    audit = after.get("/api/audit").json()
    assert any(d["target_id"] == "FR-LOAN-001" for d in audit["decisions"])
    assert any(e["event_type"] == "deletion" and gone["id"] in e["payload"] for e in audit["events"])


def test_a_running_project_cannot_be_deleted():
    release = threading.Event()
    app = server.create_app(store=in_memory_store(),
                            llm_factory=lambda backend, model: FakeLLMClient(responder=lambda s, p: release.wait() and _responder(s, p)))
    client = TestClient(app)
    started = client.post("/api/analyses", json={"transcript": TRANSCRIPT, "stakeholder_role": "loan_officer"}).json()
    try:
        assert client.delete(f"/api/analyses/{started['id']}").status_code == 409
    finally:
        release.set()


def test_a_run_cut_off_by_a_restart_reopens_as_failed():
    store, release = in_memory_store(), threading.Event()

    def stuck(backend, model):
        release.wait(5)
        return FakeLLMClient(responder=_responder)
    started = TestClient(server.create_app(store=store, llm_factory=stuck)).post(
        "/api/analyses", json={"transcript": TRANSCRIPT})
    view = TestClient(server.create_app(store=store)).get(f"/api/analyses/{started.json()['id']}").json()
    release.set()
    assert view["status"] == "failed" and "server stopped" in view["error"]


def test_audit_can_be_scoped_to_one_analysis(client):
    first, second = _analyse(client), _analyse(client)
    for view in (first, second):
        req_id = view["requirements"][0]["id"]
        client.post(f"/api/analyses/{view['id']}/requirements/{req_id}/decision",
                    json={"action": "accept", "actor_role": "product_owner"})
    client.post(f"/api/analyses/{first['id']}/sdlc/signoff", json={"actor_role": "architect"})
    everything = client.get("/api/audit").json()
    scoped = client.get(f"/api/audit?analysis={first['id']}").json()
    assert {d["target_id"] for d in scoped["decisions"]} == {
        first["requirements"][0]["id"], f"{first['id']}:{first['sdlc']['chosen']}"}
    assert 0 < len(scoped["events"]) < len(everything["events"])
    assert client.get("/api/audit?analysis=nope").status_code == 404


def test_built_front_end_is_never_served_stale(tmp_path):
    # No Cache-Control let browsers reuse an old index.html (and its old bundle) after a rebuild.
    from fastapi import FastAPI
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "assets" / "index-abc123.js").write_text("x", encoding="utf-8")
    app = FastAPI()
    app.mount("/", server.AppFiles(directory=str(tmp_path), html=True))
    c = TestClient(app)
    assert c.get("/").headers["cache-control"] == "no-cache"
    assert c.get("/index.html").headers["cache-control"] == "no-cache"
    assert "immutable" in c.get("/assets/index-abc123.js").headers["cache-control"]
