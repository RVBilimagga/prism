"""Tests for GroqClient and the Groq model list. requests is monkeypatched: no
network calls, and the "key" is a throwaway placeholder."""
from __future__ import annotations

import pytest

from finreq import llm
from finreq.llm import GroqClient, LLMError, build_llm_client, groq_models

KEY = "test-placeholder-not-a-real-key"


class _FakeResponse:
    def __init__(self, json_body: dict, status_code: int = 200, headers: dict | None = None):
        self._json_body = json_body
        self.status_code = status_code
        self.headers = headers or {}
        self.text = str(json_body)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_body


def test_missing_api_key_env_raises_with_helpful_message(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMError, match="GROQ_API_KEY is not set"):
        GroqClient()


def test_generate_sends_an_openai_style_request_with_the_key_only_in_the_header(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json)
        return _FakeResponse({"choices": [{"message": {"content": '{"a": 1}'}}]})

    monkeypatch.setattr("finreq.llm.requests.post", fake_post)
    assert GroqClient(model="openai/gpt-oss-120b").generate("system prompt", "user prompt") == '{"a": 1}'
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["headers"] == {"Authorization": f"Bearer {KEY}"}
    assert captured["json"]["model"] == "openai/gpt-oss-120b"
    assert captured["json"]["messages"] == [{"role": "system", "content": "system prompt"},
                                            {"role": "user", "content": "user prompt"}]
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["reasoning_effort"] == "low"
    assert KEY not in captured["url"] and KEY not in str(captured["json"])


def test_reasoning_effort_is_only_sent_to_gpt_oss_models(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    captured = {}
    monkeypatch.setattr("finreq.llm.requests.post", lambda url, headers=None, json=None, timeout=None: (
        captured.update(json=json) or _FakeResponse({"choices": [{"message": {"content": "{}"}}]})))
    GroqClient(model="qwen/qwen3.8-27b").generate("s", "p")
    assert "reasoning_effort" not in captured["json"]


def test_http_error_becomes_readable_llm_error_without_the_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr("finreq.llm.requests.post", lambda *a, **k: _FakeResponse(
        {"error": {"message": "Invalid API Key", "type": "invalid_request_error"}}, status_code=401))
    with pytest.raises(LLMError) as err:
        GroqClient().generate("s", "p")
    assert "401" in str(err.value) and "Invalid API Key" in str(err.value)
    assert KEY not in str(err.value)


def test_rate_limits_wait_for_retry_after_but_at_least_the_backoff(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    limited = {"error": {"message": "Rate limit reached"}}
    replies = [_FakeResponse(limited, 429, {"retry-after": "2"}), _FakeResponse(limited, 429, {"retry-after": "30"}),
               _FakeResponse({"choices": [{"message": {"content": "ok"}}]})]
    waits = []
    monkeypatch.setattr("finreq.llm.requests.post", lambda *a, **k: replies.pop(0))
    monkeypatch.setattr("finreq.llm.time.sleep", waits.append)
    assert GroqClient().generate("s", "p") == "ok"
    assert waits == [5, 30]


def test_a_spent_daily_quota_fails_at_once(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr("finreq.llm.requests.post", lambda *a, **k: _FakeResponse(
        {"error": {"message": "Rate limit reached for requests per day (RPD)"}}, 429, {"retry-after": "3600"}))
    monkeypatch.setattr("finreq.llm.time.sleep", lambda s: pytest.fail("must not wait out a daily quota"))
    with pytest.raises(LLMError, match="requests per day"):
        GroqClient().generate("s", "p")


def test_build_llm_client_knows_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    client = build_llm_client("groq", "openai/gpt-oss-20b")
    assert isinstance(client, GroqClient) and client.model == "openai/gpt-oss-20b"


def test_models_lists_the_default_first_then_active_chat_models(monkeypatch):
    llm._groq_models_cache.clear()
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    seen = {}
    body = {"data": [{"id": "whisper-large-v3", "active": True}, {"id": "qwen/qwen3.8-27b", "active": True},
                     {"id": "openai/gpt-oss-120b", "active": True}, {"id": "old/model", "active": False},
                     {"id": "meta-llama/llama-prompt-guard-2-22m", "active": True}, {"id": "openai/gpt-oss-20b"}]}

    def fake_get(url, headers=None, timeout=None):
        seen.update(url=url, headers=headers)
        return _FakeResponse(body)

    monkeypatch.setattr("finreq.llm.requests.get", fake_get)
    assert [m["id"] for m in groq_models()] == ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
    assert seen["url"] == "https://api.groq.com/openai/v1/models" and seen["headers"] == {"Authorization": f"Bearer {KEY}"}


def test_models_without_a_key_offer_only_the_default(monkeypatch):
    llm._groq_models_cache.clear()
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr("finreq.llm.requests.get", lambda *a, **k: pytest.fail("no key: must not call Groq"))
    assert [m["id"] for m in groq_models()] == ["openai/gpt-oss-120b"]
