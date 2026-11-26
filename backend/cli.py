#!/usr/bin/env python
r"""Headless pipeline runner.

Usage:
    python cli.py --transcript data/fixtures/loan_officer_interview.txt \
        --role loan_officer --domain LOAN --out out/

    # Use Google's hosted Gemini API instead of local Ollama (you must set
    # GEMINI_API_KEY yourself first — this project never stores that value):
    python cli.py --transcript data/fixtures/loan_officer_interview.txt \
        --role loan_officer --backend gemini --model gemini-3.5-flash-lite

Runs the full FinReq pipeline against a stakeholder transcript, prints a
running progress line per stage plus a summary, and writes every generated
artefact to --out.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from finreq.agents.approval import SDLC_APPROVER_ROLES
from finreq.artifacts import generate_all_artifacts
from finreq.config import SETTINGS
from finreq.sdlc import derive_factors, rank, render_plan
from finreq.llm import build_llm_client
from finreq.pipeline import run_pipeline
from finreq.retrieval import KnowledgeBase
from finreq.storage import Store


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # model names use an en dash; cp1252 pipes mangle it
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--transcript", required=True, help="Path to a stakeholder transcript text file.")
    parser.add_argument("--role", required=True, help="Stakeholder role, e.g. loan_officer, security_officer.")
    parser.add_argument("--domain", default="LOAN", help="Domain tag used in requirement IDs (e.g. LOAN, KYC).")
    parser.add_argument("--out", default="out", help="Directory to write generated artefacts to.")
    parser.add_argument("--db", default=SETTINGS.db_path, help="SQLite database path.")
    parser.add_argument("--no-clarify", action="store_true", help="Skip the clarifying-questions pass.")
    parser.add_argument("--backend", default=SETTINGS.llm_backend, choices=["ollama", "gemini", "groq"],
                         help="Which LLM backend to use (default: %(default)s).")
    parser.add_argument("--model", default=None,
                         help="Override the model for the chosen backend (e.g. qwen2.5:3b-instruct, gemini-3.5-flash-lite, openai/gpt-oss-120b).")
    parser.add_argument("--profile", default=None,
                         help="JSON file of SDLC project-profile factors (0-1), e.g. data/fixtures/loan_project_profile.json.")
    args = parser.parse_args()

    with open(args.transcript, encoding="utf-8") as f:
        transcript = f.read()
    if not transcript.strip():
        sys.exit(f"{args.transcript} is empty; there is nothing to analyse.")
    profile = {}
    if args.profile:
        with open(args.profile, encoding="utf-8") as f:
            profile = json.load(f)
        if not isinstance(profile, dict):
            sys.exit(f"--profile must be a JSON object of factor: value, got {type(profile).__name__}")
        profile = {k: v for k, v in profile.items() if not k.startswith("_")}
        try:
            derive_factors([], profile)  # fail now, not after minutes of model calls
        except ValueError as exc:
            sys.exit(f"--profile: {exc}")

    store = Store(args.db)
    llm = build_llm_client(args.backend, args.model)
    print(f"Backend: {args.backend} | model: {llm.model}\n")

    def _on_stage(label: str) -> None:
        print(f"  [{time.strftime('%H:%M:%S')}] {label}")

    result = run_pipeline(
        transcript,
        stakeholder_role=args.role,
        domain_tag=args.domain,
        llm=llm,
        kb=KnowledgeBase(),
        store=store,
        ask_clarifying_questions=not args.no_clarify,
        on_stage=_on_stage,
    )

    print(f"\nExtracted {len(result.requirements)} requirement(s):")
    for req in result.requirements:
        print(f"  {req.id} [{req.approval_status.value}] {req.statement}")

    if result.clarification.questions:
        print("\nClarifying questions for the stakeholder:")
        for q in result.clarification.questions:
            print(f"  - ({q.topic}) {q.question}")

    factors = derive_factors(result.requirements, profile)
    ranking = rank(factors)
    print("\nSDLC recommendation (needs sign-off by "
          f"{', '.join(r.replace('_', ' ') for r in SDLC_APPROVER_ROLES)}):")
    for s in ranking[:3]:
        print(f"  {s.score:5.1f}%  {s.name}")
    plan = render_plan(ranking, ranking[0].key, factors, set(), SDLC_APPROVER_ROLES)

    paths = generate_all_artifacts(result.requirements, result.risks, args.out,
                                   project_name=args.domain, sdlc_plan=plan)
    print(f"\nWrote {len(paths)} artefact(s) to {args.out}/:")
    for name in paths:
        print(f"  - {name}")

    store.close()


if __name__ == "__main__":
    main()
