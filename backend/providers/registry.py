"""Research provider selection for the Phase 2 offline vertical slice."""

from __future__ import annotations

from pathlib import Path

from .base import ResearchProvider
from .sec_edgar import FixtureSecEdgarProvider


def get_research_provider(symbol: str) -> ResearchProvider:
    """Return the deterministic provider for a symbol.

    The registry is deliberately fixture-only for now. A live SEC adapter can
    implement the same ``ResearchProvider`` contract later without changing the
    runtime or API response shape, after external access is explicitly approved.
    """
    fixture_path = Path(__file__).resolve().parents[1] / "data" / "fixtures"
    return FixtureSecEdgarProvider(fixture_path)
