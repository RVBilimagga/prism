"""Sensitive-data masking.

Per the spec's ingestion step: "Sensitive information should be classified,
masked, and protected before being submitted to an LLM." This module finds
financial/personal identifiers in raw stakeholder input, replaces each
distinct value with a stable placeholder token, and returns a reversible
mapping so a human-approval UI can show real values again without ever
sending them to the model.

This is a prototype-grade regex classifier, not a production PII scanner —
documented as such in the ARCHITECTURE.md security-controls section.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Order matters: more specific patterns first, so e.g. a card number isn't
# first swallowed by the generic ACCOUNT digit-run pattern.
_PATTERNS: list[tuple[str, str]] = [
    ("EMAIL", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    ("CARD", r"\b(?:\d[ -]?){15}\d\b"),
    ("AADHAAR", r"\b\d{4}[ -]\d{4}[ -]\d{4}\b"),
    ("PAN", r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    ("IFSC", r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    ("PHONE", r"(?:\+\d{1,3}[ -]?)?\b[6-9]\d{9}\b"),
    ("ACCOUNT", r"\b\d{9,18}\b"),
]


@dataclass
class MaskingResult:
    masked_text: str
    mapping: dict[str, str] = field(default_factory=dict)  # placeholder -> original

    def unmask(self, text: str) -> str:
        for placeholder, original in self.mapping.items():
            text = text.replace(placeholder, original)
        return text


def mask_text(text: str) -> MaskingResult:
    """Replace sensitive substrings with `[LABEL_n]` placeholders.

    The same original value always maps to the same placeholder within one
    call, so an LLM can still reason about "the same account mentioned
    twice" without ever seeing the real digits.
    """
    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}
    counts: dict[str, int] = {}

    for label, pattern in _PATTERNS:
        def _replace(m: re.Match, label: str = label) -> str:
            value = m.group(0)
            if value in reverse:
                return reverse[value]
            counts[label] = counts.get(label, 0) + 1
            placeholder = f"[{label}_{counts[label]}]"
            reverse[value] = placeholder
            mapping[placeholder] = value
            return placeholder

        text = re.sub(pattern, _replace, text)

    return MaskingResult(masked_text=text, mapping=mapping)
