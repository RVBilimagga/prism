"""Tests for GeminiClient. No real network calls or real API keys are ever
used here — requests.post is monkeypatched, and the "key" set in the
environment for these tests is a throwaway placeholder string, never a
live credential."""
from __future__ import annotations

import pytest

from finreq.llm import GeminiClient, LLMError, build_llm_client


class _FakeResponse:
    def __init__(self, json_body: dict, status_code: int = 200):
        self._json_body = json_body
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_body


def test_missing_api_key_env_raises_with_helpful_message(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMError, match="GEMINI_API_KEY is not set"):
        GeminiClient()


def test_generate_extracts_text_from_gemini_response_shape(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder-not-a-real-key")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse({
            "candidates": [{"content": {"parts": [{"text": '{"a": 1}'}]}}],
        })

    monkeypatch.setattr("finreq.llm.requests.post", fake_post)
    client = GeminiClient(model="gemini-3.5-flash-lite")
    result = client.generate("system prompt", "user prompt")

    assert result == '{"a": 1}'
    assert captured["url"].endswith("gemini-3.5-flash-lite:generateContent")
    assert captured["headers"] == {"x-goog-api-key": "test-placeholder-not-a-real-key"}
    assert captured["json"]["systemInstruction"]["parts"][0]["text"] == "system prompt"
    assert captured["json"]["contents"][0]["parts"][0]["text"] == "user prompt"
    assert captured["json"]["generationConfig"]["responseMimeType"] == "application/json"
    # The key travels only in the header: never in the URL (which ends up in
    # exception text) and never in the body.
    assert "test-placeholder" not in captured["url"]
    assert "test-placeholder" not in str(captured["json"])


def test_http_error_becomes_readable_llm_error_without_the_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder-not-a-real-key")
    monkeypatch.setattr("finreq.llm.requests.post", lambda *a, **k: _FakeResponse(
        {"error": {"code": 403, "message": "Permission denied on resource."}}, status_code=403))
    with pytest.raises(LLMError) as exc:
        GeminiClient().generate("system", "prompt")
    message = str(exc.value)
    assert "403" in message and "Permission denied" in message
    assert "test-placeholder" not in message


def test_generate_raises_on_empty_candidates(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder-not-a-real-key")
    monkeypatch.setattr(
        "finreq.llm.requests.post",
        lambda *a, **k: _FakeResponse({"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}),
    )
    client = GeminiClient()
    with pytest.raises(LLMError, match="no candidates"):
        client.generate("system", "prompt")


def test_generate_json_end_to_end_with_gemini_via_fake_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder-not-a-real-key")
    monkeypatch.setattr(
        "finreq.llm.requests.post",
        lambda *a, **k: _FakeResponse({
            "candidates": [{"content": {"parts": [{"text": '```json\n{"categories": ["security"]}\n```'}]}}],
        }),
    )
    client = GeminiClient()
    assert client.generate_json("system", "prompt") == {"categories": ["security"]}


def test_build_llm_client_ollama_backend():
    from finreq.llm import OllamaClient
    client = build_llm_client("ollama", model="some-model")
    assert isinstance(client, OllamaClient)
    assert client.model == "some-model"


def test_build_llm_client_gemini_backend(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder-not-a-real-key")
    client = build_llm_client("gemini", model="gemini-3.5-flash-lite")
    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-3.5-flash-lite"


def test_build_llm_client_rejects_unknown_backend():
    with pytest.raises(ValueError, match="unknown LLM backend"):
        build_llm_client("chatgpt")


def test_rate_limit_and_overload_wait_then_succeed(monkeypatch):
    # Found live: a free-tier key allows 15 requests a minute and one analysis
    # makes more, so the run died with a 429 four stages in.
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder-not-a-real-key")
    sleeps = []
    monkeypatch.setattr("finreq.llm.time.sleep", sleeps.append)

    def limited(delay):
        return _FakeResponse({"error": {"code": 429, "message": "Quota exceeded.", "details": [
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": delay}]}}, status_code=429)

    ok = _FakeResponse({"candidates": [{"content": {"parts": [{"text": '{"a": 1}'}]}}]})
    # Also found live: gemini-3.8-flash answered 503 "high demand" with no RetryInfo.
    busy = _FakeResponse({"error": {"code": 503, "message": "high demand"}}, status_code=503)
    # And Google's hint can be under a second while the minute is still full,
    # so waits back off from 5s regardless: 5, then 10 (> the 9s+1 hint), then 20.
    replies = iter([limited("0.696s"), limited("9s"), busy, ok])
    monkeypatch.setattr("finreq.llm.requests.post", lambda *a, **k: next(replies))
    assert GeminiClient().generate("system", "prompt") == '{"a": 1}'
    assert sleeps == [5, 10.0, 20]

    # A daily quota asks for hours: fail at once with Google's message.
    sleeps.clear()
    monkeypatch.setattr("finreq.llm.requests.post", lambda *a, **k: limited("3600s"))
    with pytest.raises(LLMError, match="429"):
        GeminiClient().generate("system", "prompt")
    assert sleeps == []


def test_dotenv_loads_values_without_overriding_the_shell(tmp_path, monkeypatch):
    import os

    from finreq.config import load_dotenv
    env = tmp_path / ".env"
    # A BOM, as Notepad and PowerShell can write one, must not break the first key.
    env.write_text('﻿FINREQ_T1="from-file"\n# comment\nFINREQ_T2=from-file\n', encoding="utf-8")
    monkeypatch.delenv("FINREQ_T1", raising=False)
    monkeypatch.setenv("FINREQ_T2", "from-shell")
    load_dotenv(env)
    assert os.environ["FINREQ_T1"] == "from-file"
    assert os.environ["FINREQ_T2"] == "from-shell"
    monkeypatch.delenv("FINREQ_T1")
