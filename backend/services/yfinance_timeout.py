"""Bound yfinance's per-ticker HTTP calls to the configured timeout."""

from __future__ import annotations

from typing import Any


def configure_yfinance_timeout(ticker: Any, timeout_seconds: float) -> Any:
    """Cap internal YfData request timeouts for one ticker instance.

    yfinance exposes timeout for some public methods, but several properties
    call YfData with their own defaults. Wrapping the instance keeps the policy
    local and avoids changing yfinance globals or leaving timed-out threads.
    """
    data = getattr(ticker, "_data", None)
    if data is None:
        return ticker

    timeout = max(1.0, float(timeout_seconds))
    for name in ("get", "post", "get_raw_json", "cache_get"):
        original = getattr(data, name, None)
        if not callable(original) or getattr(original, "_copilot_timeout_bound", False):
            continue

        def bounded(*args, __original=original, **kwargs):
            requested = kwargs.get("timeout", timeout)
            kwargs["timeout"] = min(float(requested), timeout)
            return __original(*args, **kwargs)

        bounded._copilot_timeout_bound = True
        setattr(data, name, bounded)
    return ticker
