#!/usr/bin/env python
"""Evaluation harness for the FinReq prototype.

Two kinds of evaluation, matching the spec's "Test and evaluate the
system" section:

1. Offline benchmarks (default, fast, no LLM): replay `quality_benchmark.json`
   through the rule-based QualityCheckAgent and `conflict_benchmark.json`
   through ConflictDetectionAgent, and score precision/recall against the
   hand-labeled expected outcome. These measure ambiguity/incompleteness/
   duplication/conflict-detection accuracy deterministically.

2. Live extraction eval (--live, needs Ollama running): runs the full
   pipeline against data/fixtures/loan_officer_interview.txt with the real
   configured model, matches extracted requirements to gold_requirements.json
   by TF-IDF similarity, and reports requirement extraction precision/
   recall/F1, regulatory-control coverage, and processing time.

Usage:
    python eval/evaluate.py                 # offline benchmarks only
    python eval/evaluate.py --live           # also run the live extraction eval
    python eval/evaluate.py --live --model qwen2.5-coder:7b
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from finreq.agents.conflict import ConflictDetectionAgent
from finreq.agents.quality import QualityCheckAgent
from finreq.config import SETTINGS
from finreq.models import Requirement
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_HERE = os.path.dirname(__file__)
_MATCH_THRESHOLD = 0.30


def _load_json(name: str):
    with open(os.path.join(_HERE, name), encoding="utf-8") as f:
        return json.load(f)


def _prf1(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "tp": tp, "fp": fp, "fn": fn}


def run_quality_benchmark() -> dict:
    cases = _load_json("quality_benchmark.json")
    agent = QualityCheckAgent(ctx=None)
    per_case = []
    tp = fp = fn = 0
    for case in cases:
        req = Requirement(
            id=case["id"], statement=case["statement"], source_stakeholder="benchmark",
            acceptance_criteria=case["acceptance_criteria"],
            business_justification=case["business_justification"],
            source_excerpt=case["source_excerpt"],
        )
        actual_types = {i.issue_type.value for i in agent.run(req)}
        expected_types = set(case["expected_issue_types"])
        tp += len(actual_types & expected_types)
        fp += len(actual_types - expected_types)
        fn += len(expected_types - actual_types)
        per_case.append({
            "id": case["id"], "expected": sorted(expected_types),
            "actual": sorted(actual_types), "exact_match": actual_types == expected_types,
        })
    metrics = _prf1(tp, fp, fn)
    metrics["cases_exact_match"] = sum(c["exact_match"] for c in per_case)
    metrics["cases_total"] = len(per_case)
    metrics["per_case"] = per_case
    return metrics


def run_conflict_benchmark() -> dict:
    cases = _load_json("conflict_benchmark.json")
    agent = ConflictDetectionAgent(ctx=None)
    correct = 0
    per_case = []
    for case in cases:
        a = Requirement(id="A", statement=case["a"], source_stakeholder="benchmark")
        b = Requirement(id="B", statement=case["b"], source_stakeholder="benchmark")
        agent.run([a, b])
        if b.duplicate_of == "A":
            actual = "duplicate"
        elif "B" in a.conflicts_with:
            actual = "conflict"
        else:
            actual = "none"
        is_correct = actual == case["expected"]
        correct += is_correct
        per_case.append({"id": case["id"], "expected": case["expected"], "actual": actual, "correct": is_correct})
    return {"accuracy": round(correct / len(cases), 3), "cases_total": len(cases),
            "cases_correct": correct, "per_case": per_case}


def _best_similarity(query: str, candidates: list[str]) -> tuple[int, float]:
    if not candidates:
        return -1, 0.0
    vec = TfidfVectorizer(stop_words="english")
    matrix = vec.fit_transform([query] + candidates)
    sims = cosine_similarity(matrix[0:1], matrix[1:])[0]
    idx = int(sims.argmax())
    return idx, float(sims[idx])


def run_live_extraction_eval(model: str | None = None, backend: str | None = None) -> dict:
    from finreq.llm import build_llm_client
    from finreq.pipeline import run_pipeline
    from finreq.retrieval import KnowledgeBase
    from finreq.storage import in_memory_store

    gold = _load_json("gold_requirements.json")
    with open(os.path.join(_HERE, "..", gold["transcript"]), encoding="utf-8") as f:
        transcript = f.read()

    llm = build_llm_client(backend, model)
    start = time.time()
    result = run_pipeline(
        transcript, stakeholder_role=gold["stakeholder_role"], domain_tag=gold["domain_tag"],
        llm=llm, kb=KnowledgeBase(), store=in_memory_store(), ask_clarifying_questions=False,
    )
    elapsed = time.time() - start

    gold_statements = [g["statement"] for g in gold["requirements"]]
    extracted_statements = [r.statement for r in result.requirements]

    matched_gold: set[int] = set()
    matched_extracted: set[int] = set()
    for i, stmt in enumerate(extracted_statements):
        idx, score = _best_similarity(stmt, gold_statements)
        if score >= _MATCH_THRESHOLD:
            matched_gold.add(idx)
            matched_extracted.add(i)

    tp = len(matched_extracted)
    fp = len(extracted_statements) - tp
    fn = len(gold_statements) - len(matched_gold)
    metrics = _prf1(tp, fp, fn)

    reg_relevant_ids = {g["statement"] for g in gold["requirements"] if g["regulatory_relevant"]}
    reg_extracted = [
        r for i, r in enumerate(result.requirements)
        if i in matched_extracted and gold["requirements"][
            _best_similarity(r.statement, gold_statements)[0]
        ]["regulatory_relevant"]
    ]
    reg_covered = sum(1 for r in reg_extracted if any(m.gap is None for m in r.compliance_mappings))
    metrics["regulatory_control_coverage"] = (
        round(reg_covered / len(reg_extracted), 3) if reg_extracted else None
    )
    metrics["regulatory_relevant_gold_count"] = len(reg_relevant_ids)

    metrics["requirement_count_extracted"] = len(extracted_statements)
    metrics["requirement_count_gold"] = len(gold_statements)
    metrics["processing_time_seconds"] = round(elapsed, 2)
    metrics["needs_clarification_count"] = sum(
        1 for r in result.requirements if r.approval_status.value == "needs_clarification"
    )
    metrics["model"] = llm.model
    metrics["backend"] = backend or SETTINGS.llm_backend
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Also run the live extraction eval.")
    parser.add_argument("--backend", default=None, choices=["ollama", "gemini", "groq"],
                         help="LLM backend for the live eval (default: SETTINGS.llm_backend, i.e. ollama).")
    parser.add_argument("--model", default=None, help="Override the model for the chosen backend.")
    parser.add_argument("--out", default=os.path.join(_HERE, "results"), help="Directory for the report.")
    args = parser.parse_args()

    report: dict = {
        "quality_benchmark": run_quality_benchmark(),
        "conflict_benchmark": run_conflict_benchmark(),
    }
    if args.live:
        report["live_extraction_eval"] = run_live_extraction_eval(args.model, args.backend)

    os.makedirs(args.out, exist_ok=True)
    json_path = os.path.join(args.out, "eval_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md_path = os.path.join(args.out, "eval_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# FinReq Evaluation Report\n\n")
        qb = report["quality_benchmark"]
        f.write("## Quality-check benchmark (deterministic, no LLM)\n\n")
        f.write(f"- Precision: {qb['precision']}, Recall: {qb['recall']}, F1: {qb['f1']}\n")
        f.write(f"- Exact-match cases: {qb['cases_exact_match']}/{qb['cases_total']}\n\n")
        cb = report["conflict_benchmark"]
        f.write("## Conflict-detection benchmark (deterministic, no LLM)\n\n")
        f.write(f"- Accuracy: {cb['accuracy']} ({cb['cases_correct']}/{cb['cases_total']})\n\n")
        if "live_extraction_eval" in report:
            le = report["live_extraction_eval"]
            f.write(f"## Live extraction eval (backend: {le['backend']}, model: {le['model']})\n\n")
            f.write(f"- Precision: {le['precision']}, Recall: {le['recall']}, F1: {le['f1']}\n")
            f.write(f"- Extracted {le['requirement_count_extracted']} vs {le['requirement_count_gold']} gold requirements\n")
            f.write(f"- Regulatory control coverage: {le['regulatory_control_coverage']}\n")
            f.write(f"- Needing clarification: {le['needs_clarification_count']}\n")
            f.write(f"- Processing time: {le['processing_time_seconds']}s\n")

    print(f"Wrote {json_path} and {md_path}")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "per_case"} for k, v in report.items()}, indent=2))


if __name__ == "__main__":
    main()
