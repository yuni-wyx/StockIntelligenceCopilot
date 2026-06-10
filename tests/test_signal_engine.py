from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def make_history(closes: list[float], volumes: list[float | None] | None = None) -> list[dict]:
    if volumes is None:
        volumes = [1000.0] * len(closes)
    return [
        {
            "date": f"d{index:03d}",
            "close": float(close),
            "volume": volumes[index - 1],
        }
        for index, close in enumerate(closes, start=1)
    ]


class SignalEngineTest(unittest.TestCase):
    def test_feature_calculations_are_computed_from_history(self) -> None:
        from backend.services.signal_engine import build_signal_response

        ticker_history = make_history(
            list(range(1, 61)),
            volumes=[float(value) for value in range(100, 160)],
        )
        benchmark_history = make_history(list(range(101, 161)))

        result = build_signal_response(
            ticker="TEST",
            benchmark="SPY",
            horizon_days=30,
            ticker_history=ticker_history,
            benchmark_history=benchmark_history,
        )
        snapshot = result.feature_snapshot

        self.assertAlmostEqual(snapshot.ticker_return_5d or 0, 9.09, places=2)
        self.assertAlmostEqual(snapshot.ticker_return_20d or 0, 50.0, places=2)
        self.assertAlmostEqual(snapshot.benchmark_return_20d or 0, 14.29, places=2)
        self.assertAlmostEqual(snapshot.relative_return_20d or 0, 35.71, places=2)
        self.assertAlmostEqual(snapshot.price_vs_sma20_pct or 0, 18.81, places=2)
        self.assertAlmostEqual(snapshot.sma20_vs_sma50_pct or 0, 42.25, places=2)
        self.assertAlmostEqual(snapshot.drawdown_from_60d_high_pct or 0, 0.0, places=2)
        self.assertAlmostEqual(snapshot.volume_ratio_5d_20d or 0, 1.05, places=2)
        self.assertIsNotNone(snapshot.realized_volatility_20d)

    def test_strong_neutral_and_weak_scores_are_ordered(self) -> None:
        from backend.services.signal_engine import build_signal_response

        strong = build_signal_response(
            ticker="STRONG",
            ticker_history=make_history(list(range(100, 160))),
            benchmark_history=make_history(list(range(100, 130)) + [129.0] * 30),
        )
        neutral = build_signal_response(
            ticker="NEUTRAL",
            ticker_history=make_history([100.0] * 60),
            benchmark_history=make_history([100.0] * 60),
        )
        weak = build_signal_response(
            ticker="WEAK",
            ticker_history=make_history([100.0] * 40 + list(range(20, 0, -1))),
            benchmark_history=make_history([100.0] * 60),
        )

        self.assertGreater(strong.signal_score, neutral.signal_score)
        self.assertGreater(neutral.signal_score, weak.signal_score)
        self.assertEqual(strong.signal_band, "Strong")
        self.assertEqual(neutral.signal_band, "Neutral")
        self.assertEqual(weak.signal_band, "Weak")

    def test_extreme_weak_case_clamps_score_at_zero(self) -> None:
        from backend.services.signal_engine import build_signal_response

        ticker_history = make_history(
            [100.0] * 40
            + [
                80.0,
                60.0,
                40.0,
                20.0,
                10.0,
                8.0,
                6.0,
                4.0,
                2.0,
                1.0,
                0.8,
                0.6,
                0.5,
                0.4,
                0.3,
                0.2,
                0.15,
                0.1,
                0.08,
                0.05,
            ],
            volumes=[1000.0] * 40 + [2000.0] * 20,
        )
        benchmark_history = make_history([100.0] * 60)

        result = build_signal_response(
            ticker="CLAMP",
            ticker_history=ticker_history,
            benchmark_history=benchmark_history,
        )

        self.assertGreaterEqual(result.signal_score, 0.0)
        self.assertLessEqual(result.signal_score, 100.0)
        self.assertEqual(result.signal_score, 0.0)

    def test_missing_volume_adds_caveat(self) -> None:
        from backend.services.signal_engine import build_signal_response

        ticker_history = make_history(list(range(100, 160)), volumes=[None] * 60)
        benchmark_history = make_history([100.0] * 60)

        result = build_signal_response(
            ticker="NOVOL",
            ticker_history=ticker_history,
            benchmark_history=benchmark_history,
        )

        self.assertIn("Volume confirmation was unavailable.", result.data_caveats)

    def test_short_history_downgrades_confidence(self) -> None:
        from backend.services.signal_engine import build_signal_response

        ticker_history = make_history(list(range(100, 155)))
        benchmark_history = make_history([100.0] * 55)

        result = build_signal_response(
            ticker="SHORT",
            ticker_history=ticker_history,
            benchmark_history=benchmark_history,
        )

        self.assertEqual(result.confidence, "Medium")
        self.assertIn(
            "History length was shorter than ideal for medium-term trend confirmation.",
            result.data_caveats,
        )

    def test_conflicting_signals_downgrade_confidence(self) -> None:
        from backend.services.signal_engine import build_signal_response

        ticker_history = make_history([100.0] * 40 + [150.0] * 15 + [120.0] * 5)
        benchmark_history = make_history([100.0] * 60)

        result = build_signal_response(
            ticker="MIXED",
            ticker_history=ticker_history,
            benchmark_history=benchmark_history,
        )

        self.assertEqual(result.signal_band, "Neutral")
        self.assertEqual(result.confidence, "Medium")
        self.assertIn(
            "Signals were mixed across momentum, trend, and drawdown features.",
            result.data_caveats,
        )

    def test_insufficient_history_raises_value_error(self) -> None:
        from backend.services.signal_engine import build_signal_response

        with self.assertRaisesRegex(ValueError, "Insufficient ticker history"):
            build_signal_response(
                ticker="TOO_SHORT",
                ticker_history=make_history([100.0] * 19),
                benchmark_history=make_history([100.0] * 60),
            )


if __name__ == "__main__":
    unittest.main()
