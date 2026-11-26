"""ollama_models() lists the models pulled into the local Ollama server."""
import requests

from finreq import llm as llm_module
from finreq.config import SETTINGS


class _Resp:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def test_lists_pulled_models_default_first(monkeypatch):
    tags = {"models": [{"name": "gemma4:e4b"}, {"name": SETTINGS.model}, {"name": "qwen2.5-coder:7b"}]}
    monkeypatch.setattr(llm_module.requests, "get", lambda *a, **k: _Resp(tags))
    ids = [m["id"] for m in llm_module.ollama_models()]
    assert ids == [SETTINGS.model, "gemma4:e4b", "qwen2.5-coder:7b"]


def test_offline_offers_default_only(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("no ollama")
    monkeypatch.setattr(llm_module.requests, "get", boom)
    assert [m["id"] for m in llm_module.ollama_models()] == [SETTINGS.model]
