from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def _read_streaming_response(response) -> str:
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else str(chunk))
    return "".join(chunks)


class AgentStreamingTest(unittest.TestCase):
    def test_build_agent_streaming_response_serializes_runtime_events(self) -> None:
        from backend.api.agent_streaming import build_agent_streaming_response
        from backend.schemas.agent import AgentStreamEvent, AgentTask, AgentTaskType
        from backend.schemas.output_schema import TradingDecisionOutput

        task = AgentTask(task_type=AgentTaskType.TRADE, raw_query="trade TSLA", tickers=["TSLA"])

        def runtime_event_source(_task):
            yield AgentStreamEvent(type="status", message="Starting pipeline")
            yield AgentStreamEvent(
                type="final_output",
                elapsed=0.2,
                data=TradingDecisionOutput(
                    ticker="TSLA",
                    bias="Neutral",
                    buy_zone="Current reference: $100.00",
                    stop_loss="$95.00",
                    take_profit="$108.00",
                    confidence=44,
                    reasoning=["Grounded setup."],
                ),
            )

        response = build_agent_streaming_response(
            task,
            runtime_event_source,
            legacy_raw_query="trade TSLA",
            legacy_event_source=lambda _query: iter(()),
        )
        body = asyncio.run(_read_streaming_response(response))

        self.assertIn('"type": "status"', body)
        self.assertIn('"type": "final_output"', body)
        self.assertIn('"buy_zone": "Current reference: $100.00"', body)

    def test_build_agent_streaming_response_falls_back_to_legacy_stream(self) -> None:
        from backend.api.agent_streaming import build_agent_streaming_response
        from backend.schemas.agent import AgentTask, AgentTaskType

        task = AgentTask(
            task_type=AgentTaskType.RESEARCH,
            raw_query="research TSLA",
            tickers=["TSLA"],
        )

        def runtime_event_source(_task):
            raise RuntimeError("runtime failed")
            yield  # pragma: no cover

        def legacy_event_source(_query):
            yield {"type": "status", "message": "Starting pipeline", "raw_query": "research TSLA"}
            yield {
                "type": "final_output",
                "elapsed": 0.3,
                "data": {
                    "ticker": "TSLA",
                    "fundamental_summary": "Fallback summary",
                    "recent_news_summary": "",
                    "bull_case": "",
                    "bear_case": "",
                    "what_to_watch_next": [],
                    "overall_sentiment": "NEUTRAL",
                },
            }

        response = build_agent_streaming_response(
            task,
            runtime_event_source,
            legacy_raw_query="research TSLA",
            legacy_event_source=legacy_event_source,
        )
        body = asyncio.run(_read_streaming_response(response))
        payloads = [
            json.loads(line.replace("data: ", ""))
            for line in body.splitlines()
            if line.startswith("data: ")
        ]

        self.assertEqual(payloads[0]["type"], "status")
        self.assertEqual(payloads[-1]["type"], "final_output")
        self.assertEqual(payloads[-1]["data"]["ticker"], "TSLA")

    def test_streaming_response_stops_when_request_disconnects(self) -> None:
        from backend.api.agent_streaming import build_agent_streaming_response
        from backend.schemas.agent import AgentStreamEvent, AgentTask, AgentTaskType

        task = AgentTask(task_type=AgentTaskType.TRADE, raw_query="trade TSLA", tickers=["TSLA"])

        class DisconnectAfterFirstCheck:
            def __init__(self) -> None:
                self.calls = 0

            async def is_disconnected(self) -> bool:
                self.calls += 1
                return self.calls > 1

        def runtime_event_source(_task):
            yield AgentStreamEvent(type="status", message="Starting pipeline")
            yield AgentStreamEvent(type="final_output", elapsed=0.2, data={"ticker": "TSLA"})

        response = build_agent_streaming_response(
            task,
            runtime_event_source,
            legacy_raw_query="trade TSLA",
            legacy_event_source=lambda _query: iter(()),
            request=DisconnectAfterFirstCheck(),
        )
        body = asyncio.run(_read_streaming_response(response))

        self.assertIn('"type": "status"', body)
        self.assertNotIn('"type": "final_output"', body)

    def test_streaming_response_closes_runtime_generator_on_cancel(self) -> None:
        from backend.api.agent_streaming import build_agent_streaming_response
        from backend.schemas.agent import AgentStreamEvent, AgentTask, AgentTaskType

        task = AgentTask(
            task_type=AgentTaskType.RESEARCH,
            raw_query="research TSLA",
            tickers=["TSLA"],
        )
        closed = False

        def runtime_event_source(_task):
            nonlocal closed
            try:
                yield AgentStreamEvent(type="status", message="Starting pipeline")
                yield AgentStreamEvent(type="status", message="Still working")
            finally:
                closed = True

        async def read_one_and_cancel(response) -> None:
            iterator = response.body_iterator
            await anext(iterator)
            await iterator.aclose()

        response = build_agent_streaming_response(
            task,
            runtime_event_source,
            legacy_raw_query="research TSLA",
            legacy_event_source=lambda _query: iter(()),
        )

        asyncio.run(read_one_and_cancel(response))

        self.assertTrue(closed)


if __name__ == "__main__":
    unittest.main()
