from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ApiPresentationTest(unittest.TestCase):
    def test_error_output_for_explain_has_safe_shape(self) -> None:
        from backend.api.presentation import error_output

        payload = error_output("explain tsla", RuntimeError("boom"))

        self.assertEqual(payload["ticker"], "TSLA")
        self.assertEqual(payload["overall_confidence"], 0)
        self.assertEqual(payload["ranked_causes"], [])
        self.assertIn("boom", payload["price_move_summary"])

    def test_partial_research_snapshot_has_expected_fields(self) -> None:
        from backend.api.presentation import partial_output_snapshot

        class _Plan:
            tool_calls = [object(), object(), object()]

        payload = partial_output_snapshot("research nvda", "planning", plan=_Plan())

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["ticker"], "NVDA")
        self.assertEqual(payload["overall_sentiment"], "NEUTRAL")
        self.assertIn("Collecting 3 evidence sources", payload["fundamental_summary"])

    def test_trade_stream_recovery_preserves_partial_fields_when_synthesis_fails(self) -> None:
        from backend.api.presentation import build_sse_response

        def event_source(_raw_query: str):
            yield {
                "type": "partial_output",
                "stage": "aggregation",
                "data": {
                    "ticker": "2330.TW",
                    "bias": "Neutral",
                    "buy_zone": "Current reference: $1845.00",
                    "stop_loss": "Finalizing",
                    "take_profit": "Finalizing",
                    "confidence": 0,
                    "reasoning": ["Evidence aggregated. The final trade decision is being synthesized."],
                },
            }
            raise RuntimeError("Connection error.")

        response = build_sse_response("trade 2330.TW", event_source)

        async def collect_chunks():
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(collect_chunks())
        events = [
            json.loads((chunk.decode() if isinstance(chunk, bytes) else chunk).replace("data: ", "").strip())
            for chunk in chunks
        ]

        final_event = next(event for event in events if event["type"] == "final_output")
        self.assertEqual(final_event["data"]["buy_zone"], "Current reference: $1845.00")
        self.assertEqual(final_event["data"]["stop_loss"], "Finalizing")
        self.assertEqual(final_event["data"]["take_profit"], "Finalizing")
        self.assertIn("Final synthesis failed: Connection error.", final_event["data"]["reasoning"][-1])


if __name__ == "__main__":
    unittest.main()
