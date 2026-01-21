"""Adapters package for FinAgent pipeline."""

from .base import BaseAdapter
from .context import ExecutionContext, HITLDecision, DedupResult
from .dedup import DeduplicationAdapter
from .event_type import EventTypeAdapter
from .intent import IntentAdapter
from .output import OutputAdapter
from .clarity import ClarityAdapter
from .hitl import HITLDecisionAdapter
from .logger import LoggerAdapter

__all__ = [
    "BaseAdapter",
    "ExecutionContext",
    "HITLDecision",
    "DedupResult",
    "DeduplicationAdapter",
    "EventTypeAdapter",
    "IntentAdapter",
    "OutputAdapter",
    "ClarityAdapter",
    "HITLDecisionAdapter",
    "LoggerAdapter"
]
