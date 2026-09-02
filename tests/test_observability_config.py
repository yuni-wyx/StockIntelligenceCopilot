from __future__ import annotations

import os
import unittest
from unittest.mock import patch


class ObservabilityConfigTest(unittest.TestCase):
    def test_langsmith_tracing_is_disabled_by_default(self) -> None:
        with patch.dict(
            os.environ,
            {
                "LANGCHAIN_TRACING_V2": "true",
                "ENABLE_LANGSMITH_TRACING": "false",
            },
            clear=False,
        ):
            import importlib

            import backend.config as config

            importlib.reload(config)
            self.assertEqual(config.LANGCHAIN_TRACING_V2, "false")
            self.assertEqual(os.environ["LANGCHAIN_TRACING_V2"], "false")

    def test_langsmith_tracing_requires_explicit_opt_in(self) -> None:
        with patch.dict(
            os.environ,
            {"ENABLE_LANGSMITH_TRACING": "true"},
            clear=False,
        ):
            import importlib

            import backend.config as config

            importlib.reload(config)
            self.assertEqual(config.LANGCHAIN_TRACING_V2, "true")

        # Keep the test process offline for tests that run after this one.
        with patch.dict(os.environ, {"ENABLE_LANGSMITH_TRACING": "false"}, clear=False):
            importlib.reload(config)


if __name__ == "__main__":
    unittest.main()
