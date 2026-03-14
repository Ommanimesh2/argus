"""
ARGUS Agents — config from env.
Supports Claude and OpenAI; which key is required depends on LLM_PROVIDER.
"""
import logging
import os
from pathlib import Path

# Logging: level from env, used by executor, server, workflow
LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "info").strip().upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("argus")
# String for uvicorn (e.g. "info", "debug")
UVICORN_LOG_LEVEL = os.getenv("LOG_LEVEL", "info").strip().lower()

try:
    from dotenv import load_dotenv
    _env_dir = Path(__file__).resolve().parent
    load_dotenv(_env_dir / ".env")
    load_dotenv(_env_dir.parent / ".env")
except Exception:
    pass

# LLM provider: "claude" | "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude").strip().lower()
if LLM_PROVIDER not in ("claude", "openai"):
    LLM_PROVIDER = "claude"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
ORIGINS = [o.strip() for o in os.getenv("ORIGINS", "http://localhost:3000").split(",") if o.strip()]

# Audit defaults (used once pipeline is wired)
AUDIT_TIMEOUT_SECONDS = int(os.getenv("AUDIT_TIMEOUT_SECONDS", "300"))
COMMAND_TIMEOUT_SECONDS = int(os.getenv("COMMAND_TIMEOUT_SECONDS", "60"))

# Phase-3 audit mode and budgets
AUDIT_MODE = os.getenv("AUDIT_MODE", "demo").strip().lower()
if AUDIT_MODE not in ("demo", "dev"):
    AUDIT_MODE = "demo"
IS_DEMO_MODE = AUDIT_MODE == "demo"
IS_DEV_MODE = AUDIT_MODE == "dev"

INVESTIGATION_BUDGET = int(os.getenv("INVESTIGATION_BUDGET", "10" if IS_DEMO_MODE else "50"))
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "60000"))

# AWS — used by SecureToolExecutor and nodes that run AWS CLI
AWS_PROFILE = os.getenv("AWS_PROFILE", "argus").strip()
AWS_REGION = os.getenv("AWS_REGION", "us-east-1").strip()

# Per-node model selection (fast for discovery/hypothesis, deep for reasoning/report)
FAST_MODEL = os.getenv("FAST_MODEL", "claude-sonnet-4-20250514" if LLM_PROVIDER == "claude" else "gpt-4o")
DEEP_MODEL = os.getenv("DEEP_MODEL", "claude-sonnet-4-20250514" if LLM_PROVIDER == "claude" else "gpt-4o")

# LangSmith tracing (optional)
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "").strip().lower() in ("true", "1", "yes")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "").strip() or os.getenv("LANGSMITH_API_KEY", "").strip()
if LANGSMITH_TRACING and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY


def get_required_api_key() -> str:
    """Return the API key required for the selected provider; raise if missing."""
    if LLM_PROVIDER == "claude":
        if not ANTHROPIC_API_KEY:
            raise ValueError("LLM_PROVIDER=claude requires ANTHROPIC_API_KEY in .env")
        return ANTHROPIC_API_KEY
    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("LLM_PROVIDER=openai requires OPENAI_API_KEY in .env")
        return OPENAI_API_KEY
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")
