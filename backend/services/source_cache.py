"""Small process-local TTL cache for provider responses.

This is intentionally an in-process cache for the local/demo deployment.  It
avoids repeated provider calls without introducing Redis or another external
service.  Values are copied on read/write so callers cannot mutate cached
provider responses accidentally.
"""

from __future__ import annotations

import hashlib
import json
import time
from copy import deepcopy
from typing import Any


class SourceTTLCache:
    def __init__(self, *, max_entries: int = 512) -> None:
        self.max_entries = max_entries
        self._values: dict[str, tuple[float, Any]] = {}

    @staticmethod
    def make_key(source: str, request: Any) -> str:
        if hasattr(request, "model_dump"):
            payload = request.model_dump(mode="json")
        else:
            payload = request
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        digest = hashlib.sha256(serialized).hexdigest()[:24]
        return f"{source}:{digest}"

    def get(self, key: str) -> Any | None:
        cached = self._values.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if expires_at <= time.monotonic():
            self._values.pop(key, None)
            return None
        return deepcopy(value)

    def set(self, key: str, value: Any, *, ttl_seconds: int) -> None:
        self._values[key] = (time.monotonic() + ttl_seconds, deepcopy(value))
        if len(self._values) > self.max_entries:
            oldest_key = min(self._values, key=lambda item: self._values[item][0])
            self._values.pop(oldest_key, None)

    def clear(self) -> None:
        self._values.clear()


source_ttl_cache = SourceTTLCache()
