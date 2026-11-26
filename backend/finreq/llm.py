"""LLM access layer.

Every agent talks to an `LLMClient`, never to Ollama's/Gemini's HTTP API
directly. That keeps agents testable (swap in `FakeLLMClient`) and gives one
place to enforce: retry-with-repair on invalid JSON, request/response audit
logging, and a single model configuration (see config.py).

A note on API keys: nothing in this module ever accepts a live credential as
a literal string or writes one to a file. `GeminiClient` reads its key from
an environment variable the user sets themselves — see its docstring.
"""
from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional

import requests

from finreq.config import SETTINGS


class LLMError(RuntimeError):
    pass


class LLMClient(ABC):
    """Abstract interface every agent depends on."""

    @abstractmethod
    def generate(self, system: str, prompt: str) -> str:
        """Free-text generation."""

    def generate_json(self, system: str, prompt: str, max_retries: Optional[int] = None) -> dict:
        """Generation with JSON-object parsing and repair-retry.

        On a parse failure, re-prompts once per retry with the raw output
        and the error appended, asking the model to return corrected JSON
        only. This is the standard defense against LLM output that is
        almost-but-not-quite valid JSON.
        """
        retries = SETTINGS.llm_max_retries if max_retries is None else max_retries
        last_error: Optional[str] = None
        current_prompt = prompt
        for attempt in range(retries + 1):
            raw = self.generate(system, current_prompt)
            try:
                return _extract_json(raw)
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                current_prompt = (
                    f"{prompt}\n\nYour previous response was not valid JSON:\n"
                    f"---\n{raw}\n---\nError: {last_error}\n"
                    "Return ONLY a single valid JSON object/array. No prose, no markdown fences."
                )
        raise LLMError(f"LLM did not return valid JSON after {retries + 1} attempts: {last_error}")


def unwrap_single(data):
    """Small models sometimes wrap a requested JSON object in a 1-item
    array despite instructions. Unwrap it; leave anything else untouched."""
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        return data[0]
    return data


def _extract_json(raw: str):
    text = raw.strip()
    # Strip markdown code fences if the model wrapped its answer in one.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[len("json"):]
        text = text.strip()
    # Find the first balanced JSON object/array in the text, tolerating
    # leading/trailing prose the model sometimes adds despite instructions.
    start_candidates = [i for i, c in enumerate(text) if c in "{["]
    for start in start_candidates:
        opener = text[start]
        closer = "}" if opener == "{" else "]"
        depth = 0
        for end in range(start, len(text)):
            if text[end] == opener:
                depth += 1
            elif text[end] == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start:end + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break
    raise ValueError("no valid JSON object/array found in model output")


class OllamaClient(LLMClient):
    """Real backend: talks to a locally running Ollama server."""

    def __init__(self, model: Optional[str] = None, host: Optional[str] = None,
                 on_call: Optional[Callable[[str, str, str], None]] = None):
        self.model = model or SETTINGS.model
        self.host = host or SETTINGS.ollama_host
        self.on_call = on_call  # optional audit hook: (system, prompt, response) -> None

    def generate(self, system: str, prompt: str) -> str:
        resp = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"temperature": SETTINGS.llm_temperature},
            },
            timeout=SETTINGS.request_timeout_s,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        if self.on_call:
            self.on_call(system, prompt, content)
        return content


class GeminiClient(LLMClient):
    """Real backend: Google's hosted Gemini API.

    The API key is **never** a constructor argument, never a literal in
    code, and never written to a file by this project — it is read only
    from the environment variable named by `api_key_env` (default
    `GEMINI_API_KEY`), which the user sets themselves in their own shell.
    If a caller ever passes a key-shaped string into this class some other
    way, that's a bug to fix, not a feature: the whole point of this
    boundary is that FinReq's code never holds a live credential.
    """

    _ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    _RATE_LIMIT_RETRIES = 6

    def __init__(self, model: Optional[str] = None, api_key_env: Optional[str] = None):
        self.model = model or SETTINGS.gemini_model
        self.api_key_env = api_key_env or SETTINGS.gemini_api_key_env
        if not os.environ.get(self.api_key_env):
            raise LLMError(
                f"{self.api_key_env} is not set. FinReq reads the Gemini API key only "
                f"from this environment variable. Set it yourself, then retry: either "
                f"add the line {self.api_key_env}=<your key> to the gitignored .env "
                f"file at the project root, or in your shell:\n"
                f'  PowerShell:  $env:{self.api_key_env} = "<your key>"\n'
                f"  bash:        export {self.api_key_env}=<your key>"
            )

    def generate(self, system: str, prompt: str) -> str:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise LLMError(f"{self.api_key_env} was unset between construction and use.")
        # Key goes in the x-goog-api-key header, not ?key=: it is the form
        # Google documents for both standard keys and the service-account-bound
        # "auth keys" AI Studio has issued since May 2026, and it keeps the key
        # out of the URL -- and so out of any exception text the UI shows.
        for attempt in range(self._RATE_LIMIT_RETRIES + 1):
            resp = requests.post(
                self._ENDPOINT.format(model=self.model),
                headers={"x-goog-api-key": api_key},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    # Every FinReq agent expects JSON back (see generate_json).
                    "generationConfig": {"temperature": SETTINGS.llm_temperature,
                                         "responseMimeType": "application/json"},
                },
                timeout=SETTINGS.request_timeout_s,
            )
            # A free-tier key allows about 15 requests a minute, and one analysis
            # makes more than that (429); new models also shed load under high
            # demand (503). Both are temporary, so wait it out.
            wait = _retry_after(resp) if resp.status_code in (429, 503) else None
            if wait is None or attempt == self._RATE_LIMIT_RETRIES:
                break
            # Google's hint can be under a second while the per-minute window
            # is still full (found live: six 1.7s waits, then failure), so
            # back off at least 5, 10, 20, 40, 60, 60s.
            time.sleep(min(max(wait, 5 * 2 ** attempt), 60))
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except ValueError:
                detail = resp.text[:300]
            hint = {400: "check the key and the request", 401: "the key was rejected",
                    403: "the key lacks access to this model or was disabled",
                    404: f"model '{self.model}' is not available to this key",
                    429: "quota or rate limit reached; wait and retry",
                    503: "the model is overloaded; try again later or pick another model"}.get(resp.status_code, "")
            raise LLMError(f"Gemini API error {resp.status_code} ({hint}): {detail}".replace(" ()", ""))
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            feedback = data.get("promptFeedback", {})
            raise LLMError(f"Gemini returned no candidates (promptFeedback={feedback}).")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            raise LLMError(f"Gemini candidate had no text content: {candidates[0]}")
        return text


def _retry_after(resp) -> Optional[float]:
    """Seconds Google asks a rate-limited (429) or overloaded (503) call to
    wait, from its RetryInfo detail (0 when it sends none). None when the wait
    is too long to block on, such as an exhausted daily quota: that error goes
    to the user instead."""
    delay = 0.0
    try:
        for detail in resp.json()["error"].get("details", []):
            if detail.get("@type", "").endswith("google.rpc.RetryInfo"):
                delay = float(str(detail["retryDelay"]).rstrip("s")) + 1
    except (ValueError, KeyError, TypeError, AttributeError):
        pass
    return delay if delay <= 60 else None


class GroqClient(LLMClient):
    """Real backend: Groq's OpenAI-compatible chat API (fast hosted open models,
    with a free plan).

    The key follows the same rule as GeminiClient's: read only from the
    environment variable named by `api_key_env` (default GROQ_API_KEY, from
    the shell or the gitignored .env), never a constructor argument.
    """

    _BASE = "https://api.groq.com/openai/v1"
    _RATE_LIMIT_RETRIES = 6

    def __init__(self, model: Optional[str] = None, api_key_env: Optional[str] = None):
        self.model = model or SETTINGS.groq_model
        self.api_key_env = api_key_env or SETTINGS.groq_api_key_env
        if not os.environ.get(self.api_key_env):
            raise LLMError(
                f"{self.api_key_env} is not set. FinReq reads the Groq API key only "
                f"from this environment variable. Add the line {self.api_key_env}=<your key> "
                f"to the gitignored .env file at the project root, or set it in your shell, "
                f"then restart."
            )

    def generate(self, system: str, prompt: str) -> str:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise LLMError(f"{self.api_key_env} was unset between construction and use.")
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": prompt}],
            "temperature": SETTINGS.llm_temperature,
            # Every agent expects JSON (see generate_json); Groq's JSON mode.
            "response_format": {"type": "json_object"},
        }
        if self.model.startswith("openai/gpt-oss"):
            # Reasoning tokens count against the free plan's 8K tokens a minute.
            body["reasoning_effort"] = "low"
        for attempt in range(self._RATE_LIMIT_RETRIES + 1):
            resp = requests.post(f"{self._BASE}/chat/completions", json=body, timeout=SETTINGS.request_timeout_s,
                                 headers={"Authorization": f"Bearer {api_key}"})
            # The free plan allows about 30 requests and 8K tokens a minute; an
            # analysis makes ~32 calls, so wait those out. Groq's retry-after
            # says how long; one over 60s (a spent daily quota) fails at once.
            if resp.status_code not in (429, 498, 503) or attempt == self._RATE_LIMIT_RETRIES:
                break
            try:
                hint = float(resp.headers.get("retry-after", 0))
            except (TypeError, ValueError):
                hint = 0.0
            if hint > 60:
                break
            time.sleep(min(max(hint, 5 * 2 ** attempt), 60))
        if resp.status_code >= 400:
            try:
                error = resp.json().get("error", {})
                detail = error.get("message", "") if isinstance(error, dict) else str(error)
            except ValueError:
                detail = resp.text[:300]
            hint = {401: "the key was rejected", 404: f"model '{self.model}' is not available",
                    413: "the request is too large for this model's limits",
                    429: "rate limit or daily quota reached", 498: "Groq is over capacity; try again",
                    503: "Groq is unavailable; try again later"}.get(resp.status_code, "")
            raise LLMError(f"Groq API error {resp.status_code} ({hint}): {detail}".replace(" ()", ""))
        choices = resp.json().get("choices") or []
        text = (choices[0].get("message", {}).get("content") or "") if choices else ""
        if not text:
            raise LLMError(f"Groq returned no text from '{self.model}'. Try again or pick another model.")
        return text


_groq_models_cache: dict = {}
# Groq models that are not chat models: speech, text-to-speech and safety classifiers.
_NOT_CHAT = ("whisper", "orpheus", "guard")


def groq_models() -> list[dict]:
    """Groq's active chat models ({id, name}), the default first. Groq's model
    list needs the key, so the server asks with it (it never reaches the
    browser); without a key, or offline, only the default is offered. Cached
    for an hour."""
    default = {"id": SETTINGS.groq_model, "name": SETTINGS.groq_model}
    api_key = os.environ.get(SETTINGS.groq_api_key_env)
    cached = _groq_models_cache.get("models")
    if cached and time.time() - cached[0] < 3600:
        return cached[1]
    if not api_key:
        return [default]
    try:
        resp = requests.get(f"{GroqClient._BASE}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
        resp.raise_for_status()
        ids = sorted(m["id"] for m in resp.json()["data"]
                     if m.get("active", True) and not any(word in m["id"] for word in _NOT_CHAT))
    except (requests.RequestException, ValueError, KeyError, TypeError, RuntimeError):
        return [default]
    models = [default] + [{"id": i, "name": i} for i in ids if i != default["id"]]
    _groq_models_cache["models"] = (time.time(), models)
    return models


def ollama_models() -> list[dict]:
    """Models pulled into the local Ollama server ({id, name}), the configured
    default first. Offline or unreachable, only the default is offered."""
    default = {"id": SETTINGS.model, "name": SETTINGS.model}
    try:
        resp = requests.get(f"{SETTINGS.ollama_host}/api/tags", timeout=5)
        resp.raise_for_status()
        names = sorted(m["name"] for m in resp.json().get("models", []))
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return [default]
    return [default] + [{"id": n, "name": n} for n in names if n != default["id"]]


def build_llm_client(backend: Optional[str] = None, model: Optional[str] = None) -> LLMClient:
    """Factory used by server.py and cli.py so the entry points don't need to
    know each backend's constructor shape."""
    backend = (backend or SETTINGS.llm_backend).lower()
    if backend == "ollama":
        return OllamaClient(model=model)
    if backend == "gemini":
        return GeminiClient(model=model)
    if backend == "groq":
        return GroqClient(model=model)
    raise ValueError(f"unknown LLM backend '{backend}'; expected 'ollama', 'gemini' or 'groq'")


class FakeLLMClient(LLMClient):
    """Deterministic test double.

    Construct with either:
      - `responses`: a list of strings/dicts returned in call order, or
      - `responder`: a callable(system, prompt) -> str/dict for dynamic behavior.
    A dict response is auto-serialised to JSON text.
    """

    def __init__(self, responses: Optional[list] = None,
                 responder: Optional[Callable[[str, str], object]] = None):
        self.responses = list(responses or [])
        self.responder = responder
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        if self.responder is not None:
            out = self.responder(system, prompt)
        elif self.responses:
            out = self.responses.pop(0)
        else:
            raise LLMError("FakeLLMClient has no more scripted responses")
        return json.dumps(out) if isinstance(out, (dict, list)) else str(out)
