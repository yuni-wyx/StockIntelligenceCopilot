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
    timeout_positions = {"get": 2, "post": 3, "get_raw_json": 2, "cache_get": 2}
    for name in timeout_positions:
        original = getattr(data, name, None)
        if not callable(original) or getattr(original, "_copilot_timeout_bound", False):
            continue

        timeout_position = timeout_positions[name]

        def bounded(*args, __original=original, __timeout_position=timeout_position, **kwargs):
            mutable_args = list(args)
            requested = kwargs.pop("timeout", None)
            if requested is None and len(mutable_args) > __timeout_position:
                requested = mutable_args[__timeout_position]
            effective = min(float(requested if requested is not None else timeout), timeout)
            if len(mutable_args) > __timeout_position:
                mutable_args[__timeout_position] = effective
            else:
                kwargs["timeout"] = effective
            return __original(*mutable_args, **kwargs)

        bounded._copilot_timeout_bound = True
        setattr(data, name, bounded)
    return ticker
