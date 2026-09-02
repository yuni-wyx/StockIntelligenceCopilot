from __future__ import annotations

import unittest

from backend.services.yfinance_timeout import configure_yfinance_timeout


class YfinanceTimeoutTest(unittest.TestCase):
    def test_internal_calls_are_capped_without_changing_other_arguments(self) -> None:
        class FakeData:
            def get(self, url, params=None, timeout=30):
                return url, params, timeout

            def post(self, url, body=None, params=None, timeout=30, data=None):
                return url, body, params, timeout, data

        class FakeTicker:
            _data = FakeData()

        ticker = configure_yfinance_timeout(FakeTicker(), 5)
        self.assertEqual(ticker._data.get("url", timeout=30), ("url", None, 5.0))
        self.assertEqual(ticker._data.get("url", None, 30), ("url", None, 5.0))
        self.assertEqual(
            ticker._data.post("url", timeout=2),
            ("url", None, None, 2.0, None),
        )

    def test_ticker_without_yf_data_is_left_unchanged(self) -> None:
        ticker = object()
        self.assertIs(configure_yfinance_timeout(ticker, 5), ticker)


if __name__ == "__main__":
    unittest.main()
