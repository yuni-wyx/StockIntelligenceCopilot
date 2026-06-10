"""
Tools package — independent, reusable data-fetching modules.
All tools return mock data with realistic financial structure.
"""

from .signal_tool import SignalToolRequest, fetch_signal

__all__ = ["SignalToolRequest", "fetch_signal"]
