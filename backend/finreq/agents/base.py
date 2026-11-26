"""Shared agent context and base class.

The "orchestrator" in this prototype (see pipeline.py) is a plain Python
function that constructs one `AgentContext` and calls each agent in turn —
there's no separate message-passing framework. Each agent is still a
distinct class with a single responsibility and its own prompt, matching
the multi-agent architecture in the spec; the orchestrator plays the role
of the coordinator agent, and every agent call is written to the shared
audit log for traceability.
"""
from __future__ import annotations

import json
from abc import ABC
from dataclasses import dataclass, field

from finreq.config import SETTINGS
from finreq.llm import LLMClient
from finreq.models import AuditEvent
from finreq.retrieval import KnowledgeBase
from finreq.storage import Store


@dataclass
class AgentContext:
    llm: LLMClient
    kb: KnowledgeBase
    store: Store
    domain_tag: str = "GEN"

    def log(self, agent: str, event_type: str, payload: dict) -> None:
        event = AuditEvent(agent=agent, event_type=event_type, payload=json.dumps(payload, default=str))
        self.store.log_event(event)


class Agent(ABC):
    name: str = "agent"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def call_llm_json(self, system: str, prompt: str) -> dict:
        result = self.ctx.llm.generate_json(system, prompt)
        self.ctx.log(self.name, "prompt", {"system": system, "prompt": prompt, "response": result})
        return result
