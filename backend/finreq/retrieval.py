"""Retrieval-grounded generation support.

Loads every document under `data/knowledge_base/`, each of which must start
with a small metadata header (source, jurisdiction, effective_date, version,
applicability) per the spec's "every knowledge item should include its
source, jurisdiction, effective date, version, and applicability."

Retrieval uses TF-IDF + cosine similarity (scikit-learn) rather than a vector
database — deliberately, for a dependency-free, fully offline prototype. The
`KnowledgeBase` interface is small enough that swapping in a real vector
store (chromadb, pgvector, ...) later only touches this one file.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from finreq.config import SETTINGS
from finreq.models import Evidence

_HEADER_FIELDS = ("source", "jurisdiction", "effective_date", "version", "applicability")

# Every requirement statement is boilerplate-shaped ("The system shall...")
# and every policy document is written in the same register, so plain
# English stopwords aren't enough — "system", "shall", "customer" etc.
# appear in nearly every document and swamp the genuinely distinguishing
# terms. Stripping them noticeably widens the gap between an on-topic match
# and an unrelated one (verified empirically against the sample KB).
DOMAIN_STOP_WORDS = list(ENGLISH_STOP_WORDS.union({
    "system", "shall", "must", "will", "should", "requirement", "requirements",
    "customer", "customers",
}))


@dataclass
class KBDocument:
    doc_id: str
    title: str
    jurisdiction: str
    effective_date: str
    version: str
    applicability: str
    body: str


def _parse_document(path: str) -> KBDocument:
    with open(path, encoding="utf-8") as f:
        text = f.read()

    header: dict[str, str] = {}
    body_lines: list[str] = []
    in_header = True
    for line in text.splitlines():
        if in_header:
            m = re.match(r"^(\w+):\s*(.*)$", line.strip())
            if m and m.group(1).lower() in _HEADER_FIELDS:
                header[m.group(1).lower()] = m.group(2).strip()
                continue
            if line.strip() == "---":
                in_header = False
                continue
            if not m and line.strip():
                # First non-header line ends the header even without '---'.
                in_header = False
                body_lines.append(line)
                continue
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    doc_id = os.path.splitext(os.path.basename(path))[0]
    title = header.get("source", doc_id)
    return KBDocument(
        doc_id=doc_id,
        title=title,
        jurisdiction=header.get("jurisdiction", "unknown"),
        effective_date=header.get("effective_date", "unknown"),
        version=header.get("version", "1.0"),
        applicability=header.get("applicability", ""),
        body=body,
    )


class KnowledgeBase:
    def __init__(self, directory: str | None = None):
        self.directory = directory or SETTINGS.knowledge_base_dir
        self.documents: list[KBDocument] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._load()

    def _load(self) -> None:
        if not os.path.isdir(self.directory):
            return
        for name in sorted(os.listdir(self.directory)):
            if name.endswith(".md") or name.endswith(".txt"):
                self.documents.append(_parse_document(os.path.join(self.directory, name)))
        if self.documents:
            self._vectorizer = TfidfVectorizer(stop_words=DOMAIN_STOP_WORDS)
            self._matrix = self._vectorizer.fit_transform([d.body for d in self.documents])

    def is_empty(self) -> bool:
        return not self.documents

    def retrieve(self, query: str, top_k: int | None = None) -> list[Evidence]:
        """Return the top-k most relevant KB passages for `query`, each
        carrying its similarity score so callers can apply a confidence
        threshold (spec: "Escalate unsupported or low-confidence outputs")."""
        if self.is_empty():
            return []
        top_k = top_k or SETTINGS.retrieval_top_k
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(range(len(sims)), key=lambda i: -sims[i])[:top_k]
        evidence = []
        for i in ranked:
            doc = self.documents[i]
            score = float(sims[i])
            if score <= 0:
                continue
            evidence.append(
                Evidence(
                    source_id=doc.doc_id,
                    source_title=doc.title,
                    jurisdiction=doc.jurisdiction,
                    effective_date=doc.effective_date,
                    version=doc.version,
                    excerpt=_excerpt(doc.body),
                    similarity=round(score, 4),
                )
            )
        return evidence


def _excerpt(body: str, max_chars: int = 400) -> str:
    body = body.strip()
    return body if len(body) <= max_chars else body[:max_chars].rsplit(" ", 1)[0] + "..."
