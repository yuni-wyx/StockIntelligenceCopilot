# config.py
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
_truthy = {"1", "true", "yes", "on"}
ENABLE_LANGSMITH_TRACING = os.getenv("ENABLE_LANGSMITH_TRACING", "").strip().lower() in _truthy

# LangSmith is opt-in.  Keep the existing traceable decorators in place, but
# prevent the SDK from creating outbound runs unless explicitly enabled.
LANGCHAIN_TRACING_V2 = "true" if ENABLE_LANGSMITH_TRACING else "false"
os.environ["LANGCHAIN_TRACING_V2"] = LANGCHAIN_TRACING_V2
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "stock-copilot")
ENABLE_LLM_TRADE_SYNTHESIS = os.getenv(
    "ENABLE_LLM_TRADE_SYNTHESIS",
    "",
).strip().lower() in _truthy
ENABLE_LLM_PORTFOLIO_CHAT = os.getenv(
    "ENABLE_LLM_PORTFOLIO_CHAT",
    "",
).strip().lower() in _truthy
BACKEND_CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def _bounded_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


PROVIDER_MAX_RETRIES = _bounded_int("PROVIDER_MAX_RETRIES", 1, 0, 3)
PROVIDER_RETRY_BACKOFF_SECONDS = _bounded_float(
    "PROVIDER_RETRY_BACKOFF_SECONDS", 0.1, 0.0, 2.0
)
PROVIDER_TIMEOUT_SECONDS = _bounded_float(
    "PROVIDER_TIMEOUT_SECONDS", 15.0, 1.0, 60.0
)


def llm_trade_synthesis_enabled() -> bool:
    return os.getenv("ENABLE_LLM_TRADE_SYNTHESIS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def llm_portfolio_chat_enabled() -> bool:
    return os.getenv("ENABLE_LLM_PORTFOLIO_CHAT", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
