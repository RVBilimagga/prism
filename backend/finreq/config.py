"""Central configuration. Every tunable knob for the prototype lives here so
agents, the server and the CLI read one source of truth.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path) -> None:
    """Copy KEY=VALUE lines from a local .env file into os.environ. The
    file is gitignored (and so skipped by the secret-scan gate), which makes
    it the place for GEMINI_API_KEY. A variable already set in the shell wins."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        key = key.strip()
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key, value.strip().strip("\"'"))


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass
class Settings:
    # Ollama connection
    ollama_host: str = os.environ.get("FINREQ_OLLAMA_HOST", "http://localhost:11434")

    # Model used for structured extraction / classification / compliance /
    # risk reasoning. qwen2.5:3b-instruct is small enough to run fast on
    # modest hardware (fits in ~2-4GB VRAM) while still following JSON-shaped
    # instructions reliably — swapped in from the 7B default after measuring
    # the 7B model's per-run time in eval/results/eval_report.md; see
    # the README's measured model results for the speed/quality tradeoff.
    model: str = os.environ.get("FINREQ_MODEL", "qwen2.5:3b-instruct")

    # Larger fallback model, used nowhere by default today but kept
    # configurable for when quality matters more than speed.
    fallback_model: str = os.environ.get("FINREQ_FALLBACK_MODEL", "hhao/qwen2.5-coder-tools:7b")

    # Which LLMClient build_llm_client() constructs: "ollama" (default,
    # fully local/offline) or "gemini" (Google's hosted API — needs
    # GEMINI_API_KEY, from the shell or .env; see llm.py's GeminiClient).
    llm_backend: str = os.environ.get("FINREQ_LLM_BACKEND", "ollama")
    gemini_model: str = os.environ.get("FINREQ_GEMINI_MODEL", "gemini-3.5-flash-lite")
    # Read directly by GeminiClient, never stored on Settings or logged —
    # this attribute name is documentation, not a place a key is kept.
    gemini_api_key_env: str = "GEMINI_API_KEY"
    # "groq": Groq's hosted open models (free plan available). Same key rule as
    # Gemini (GROQ_API_KEY, shell or .env; see llm.py's GroqClient).
    groq_model: str = os.environ.get("FINREQ_GROQ_MODEL", "openai/gpt-oss-120b")
    groq_api_key_env: str = "GROQ_API_KEY"

    request_timeout_s: int = 600
    llm_temperature: float = 0.1
    llm_max_retries: int = 2

    # Requirement-quality thresholds
    duplicate_similarity_threshold: float = 0.92
    near_duplicate_similarity_threshold: float = 0.75

    # Retrieval
    knowledge_base_dir: str = str(Path(__file__).resolve().parents[1] / "data" / "knowledge_base")
    retrieval_top_k: int = 3
    # Below this TF-IDF cosine similarity, a retrieved passage is treated as
    # not actually supporting the requirement (empirically: unrelated
    # queries against the sample KB score ~0.10, the weakest genuine match
    # ~0.20 — see retrieval.py's domain stopword note).
    low_confidence_threshold: float = 0.18

    # Storage
    db_path: str = os.environ.get("FINREQ_DB_PATH", "finreq.db")


SETTINGS = Settings()
