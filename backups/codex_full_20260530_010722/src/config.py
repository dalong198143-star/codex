"""Configuration module — all hardcoded values centralized here.

Supports environment variable overrides for ports, LiteLLM URL, system prompt, etc.
"""

import os

# ── LiteLLM backend ──────────────────────────────────────────────
LITELLM_URL = os.environ.get("LITELLM_URL", "http://127.0.0.1:1235")
LITELLM_PORT = int(os.environ.get("LITELLM_PORT", "1235"))
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY")
if not LITELLM_MASTER_KEY:
    import warnings
    warnings.warn("LITELLM_MASTER_KEY not set ? LiteLLM health checks may fail without auth")
    LITELLM_MASTER_KEY = ""  # safe empty fallback


def get_litellm_headers() -> dict:
    """Return headers dict for upstream LiteLLM requests (auth if key set)."""
    if LITELLM_MASTER_KEY:
        return {"Authorization": f"Bearer {LITELLM_MASTER_KEY}"}
    return {}

# ── Proxy server ──────────────────────────────────────────────────
PROXY_HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "1234"))

# ── Model mapping ─────────────────────────────────────────────────
# Models that should be aliased to the default.
KNOWN_MODELS: set[str] = {"gpt-5.5", "gpt-5.1", "gpt-5", "o3", "o4-mini"}
DEFAULT_MODEL = "deepseek-v4-pro"

# ── Retry / timeout ───────────────────────────────────────────────
MAX_RETRIES = int(os.environ.get("CODEX_MAX_RETRIES", "2"))
UPSTREAM_TIMEOUT_CONNECT = int(os.environ.get("CODEX_TIMEOUT_CONNECT", "10"))
UPSTREAM_TIMEOUT_READ = int(os.environ.get("CODEX_TIMEOUT_READ", "180"))
UPSTREAM_TIMEOUT_TOTAL = int(os.environ.get("CODEX_TIMEOUT_TOTAL", "300"))

# ── System prompt ─────────────────────────────────────────────────
DEFAULT_SYSTEM_PROMPT = (
    "You are a coding agent. You MUST reply in Chinese (简体中文) at all times. "
    "You MUST use tools proactively to explore, read, and modify code. "
    "NEVER just chat or ask questions — take action first. "
    "Use shell commands to list files, read code, run tests. "
    "Before troubleshooting or making config changes, query the local KB first: "
    "python D:/hermes-tools/scripts/query_kb.py '<keywords>'. "
    "After solving a non-trivial problem, write the solution to KB: "
    "python D:/hermes-tools/scripts/add_to_kb.py '<content>' <topic> '<section>'. "
    "See D:/hermes-tools/KB_AGENTS.md for the full KB usage charter. "
    "\\n"
    "## Image Analysis (CRITICAL)\\n"
    "When the user sends an image and you see '[Image: source: <path>]' or any image reference:\\n"
    "  → IMMEDIATELY run: python D:/maozhua/Codex/analyze_image.py \"<path>\"\\n"
    "  → NEVER try to describe/guess the image yourself — always use the script.\\n"
    "  → The script auto-routes through qwen-vl-plus (vision model) via proxy."
)


def get_system_prompt() -> str:
    """Return the system prompt from CODEX_SYSTEM_PROMPT env var, or the default.

    Returns empty string when CODEX_SYSTEM_PROMPT is "none" or empty.
    """
    prompt = os.environ.get("CODEX_SYSTEM_PROMPT")
    if prompt is None:
        return DEFAULT_SYSTEM_PROMPT
    stripped = prompt.strip()
    if stripped == "" or stripped.lower() == "none":
        return ""
    return prompt


def is_model_aliased(model: str) -> bool:
    """Check if a model name should be remapped to the default model."""
    return model in KNOWN_MODELS
