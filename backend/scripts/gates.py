#!/usr/bin/env python
"""Delivery-pipeline gates (Agile-DevSecOps "secure delivery pipeline" phase,
see docs/SDLC.md). One command, same gates locally and in CI:

    python backend/scripts/gates.py            # all gates
    python backend/scripts/gates.py --skip-audit   # offline: skip the dependency audit (needs network)

Exits non-zero if any gate fails.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BACKEND)
# Credential shapes that must never be committed (see ARCHITECTURE.md "Credential handling").
SECRET_PATTERNS = [
    r"AIza[0-9A-Za-z_\-]{35}",               # Google API key
    r"\bAQ\.[0-9A-Za-z_\-]{30,}",             # Google OAuth-style access token
    r"\bsk-[0-9A-Za-z]{20,}",                 # common "sk-" API keys
    r"\bgsk_[0-9A-Za-z]{20,}",                # Groq API key
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]


def _run(cmd: list[str], cwd: str = ROOT) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, out.splitlines()[-1] if out else ""


def gate_tests():
    return _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])


def gate_eval():
    ok, _ = _run([sys.executable, "backend/eval/evaluate.py"])
    if not ok:
        return False, "backend/eval/evaluate.py failed"
    with open(os.path.join(BACKEND, "eval", "results", "eval_report.json"), encoding="utf-8") as f:
        report = json.load(f)
    f1, acc = report["quality_benchmark"]["f1"], report["conflict_benchmark"]["accuracy"]
    # Thresholds sit at today's measured values: a regression fails the build.
    return f1 >= 0.95 and acc >= 0.85, f"quality-check F1 {f1} (min 0.95), conflict accuracy {acc} (min 0.85)"


def gate_sast():
    ok, last = _run([sys.executable, "-m", "bandit", "-q", "-r", "backend/finreq", "backend/cli.py", "backend/server.py",
                     "backend/scripts",
                     "--severity-level", "medium"])
    return ok, last or "no medium/high findings"


def gate_web():
    npm = shutil.which("npm")
    web = os.path.join(ROOT, "frontend")
    if not npm:
        return False, "npm not found; install Node.js to type-check and build frontend/"
    if not os.path.isdir(os.path.join(web, "node_modules")):
        return False, "run `npm ci --prefix frontend` first"
    ok, last = _run([npm, "run", "build"], cwd=web)
    if not ok:
        return False, last
    ok, last = _run([npm, "audit", "--omit=dev", "--audit-level=high"], cwd=web)
    return ok, "type-check, build and npm audit clean" if ok else last


def gate_dependencies():
    return _run([sys.executable, "-m", "pip_audit", "-r", "backend/requirements.txt", "--progress-spinner", "off"])


def gate_secrets():
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True).stdout.split()
    pattern = re.compile("|".join(SECRET_PATTERNS))
    hits = []
    for rel in files:
        if rel == "backend/scripts/gates.py" or rel.endswith((".docx", ".db", ".png")):
            continue
        try:
            with open(os.path.join(ROOT, rel), encoding="utf-8", errors="ignore") as f:
                hits += [f"{rel}:{n}" for n, line in enumerate(f, 1) if pattern.search(line)]
        except OSError:
            continue
    return not hits, ", ".join(hits) or f"{len(files)} files clean"


def main() -> int:
    gates = [("Unit and integration tests", gate_tests), ("Offline quality benchmarks", gate_eval),
             ("Static security analysis (bandit)", gate_sast), ("Secret scan", gate_secrets),
             ("Front end: type-check, build, npm audit", gate_web)]
    if "--skip-audit" not in sys.argv:
        gates.append(("Dependency vulnerability audit (pip-audit)", gate_dependencies))
    failed = 0
    for name, gate in gates:
        ok, detail = gate()
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    print(f"\n{len(gates) - failed}/{len(gates)} gates passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
