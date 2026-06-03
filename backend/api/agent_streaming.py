from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi.responses import StreamingResponse

try:
    from ..api.presentation import recovery_output, serialize_output
    from ..schemas.agent import AgentStreamEvent, AgentTask
except ImportError:
    from api.presentation import recovery_output, serialize_output
    from schemas.agent import AgentStreamEvent, AgentTask

logger = logging.getLogger(__name__)


def _serialize_stream_data(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    return serialize_output(value)


def _event_payload(event: AgentStreamEvent | dict[str, Any]) -> dict[str, Any]:
    if isinstance(event, AgentStreamEvent):
        payload = event.model_dump(mode="json", exclude={"data"})
        payload["data"] = event.data
    else:
        payload = dict(event)
    if payload.get("type") == "final_output":
        payload["data"] = _serialize_stream_data(payload.get("data"))
    return payload


async def _request_disconnected(request: Any | None) -> bool:
    if request is None:
        return False
    try:
        return bool(await request.is_disconnected())
    except Exception:
        logger.exception("Failed to check SSE client disconnect state")
        return False


def _close_event_source(source: Any | None) -> None:
    close = getattr(source, "close", None)
    if close is None:
        return
    try:
        close()
    except Exception:
        logger.exception("Failed to close SSE event source")


def build_agent_streaming_response(
    task: AgentTask,
    runtime_event_source,
    *,
    legacy_raw_query: str,
    legacy_event_source,
    request: Any | None = None,
) -> StreamingResponse:
    async def event_stream():
        last_partial: dict | None = None
        runtime_source = None
        legacy_source = None
        try:
            runtime_source = runtime_event_source(task)
            for event in runtime_source:
                if await _request_disconnected(request):
                    logger.info("SSE client disconnected for query '%s'", legacy_raw_query)
                    return
                payload = _event_payload(event)
                if payload["type"] == "partial_output" and isinstance(payload.get("data"), dict):
                    last_partial = payload["data"]
                yield f"data: {json.dumps(payload, default=str)}\n\n"
        except (GeneratorExit, asyncio.CancelledError):
            logger.info("SSE stream cancelled for query '%s'", legacy_raw_query)
            raise
        except Exception:
            if await _request_disconnected(request):
                logger.info(
                    "Runtime streaming stopped after client disconnect for query '%s'",
                    legacy_raw_query,
                )
                return
            logger.exception(
                "Runtime streaming failed for query '%s'; falling back to legacy stream",
                legacy_raw_query,
            )
            try:
                legacy_source = legacy_event_source(legacy_raw_query)
                for event in legacy_source:
                    if await _request_disconnected(request):
                        logger.info(
                            "SSE client disconnected during legacy fallback for query '%s'",
                            legacy_raw_query,
                        )
                        return
                    payload = (
                        {
                            "type": "final_output",
                            "elapsed": event["elapsed"],
                            "data": _serialize_stream_data(event["data"]),
                        }
                        if event["type"] == "final_output"
                        else event
                    )
                    yield f"data: {json.dumps(payload, default=str)}\n\n"
            except (GeneratorExit, asyncio.CancelledError):
                logger.info(
                    "SSE legacy fallback stream cancelled for query '%s'",
                    legacy_raw_query,
                )
                raise
            except Exception as legacy_exc:
                if await _request_disconnected(request):
                    logger.info(
                        "Legacy streaming stopped after client disconnect for query '%s'",
                        legacy_raw_query,
                    )
                    return
                logger.exception(
                    "Legacy streaming fallback also failed for query '%s'",
                    legacy_raw_query,
                )
                yield (
                    f"data: {json.dumps({'type': 'error', 'message': str(legacy_exc)})}\n\n"
                )
                safe_event = {
                    "type": "final_output",
                    "elapsed": 0,
                    "data": recovery_output(
                        legacy_raw_query,
                        legacy_exc,
                        partial=last_partial,
                    ),
                }
                yield f"data: {json.dumps(safe_event, default=str)}\n\n"
            finally:
                _close_event_source(legacy_source)
        finally:
            _close_event_source(runtime_source)
            logger.debug("SSE stream cleanup complete for query '%s'", legacy_raw_query)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
