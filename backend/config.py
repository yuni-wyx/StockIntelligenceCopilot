# config.py
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "stock-copilot")
ENABLE_LLM_TRADE_SYNTHESIS = os.getenv(
    "ENABLE_LLM_TRADE_SYNTHESIS",
    "",
).strip().lower() in {"1", "true", "yes", "on"}
BACKEND_CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]


def llm_trade_synthesis_enabled() -> bool:
    return os.getenv("ENABLE_LLM_TRADE_SYNTHESIS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
