"""
HIVE CONFIG - Shared Configuration Management
==============================================
Single source of truth for environment variables and paths.
MidOS (L1) is the canonical project. Raphael (L0) deprecated 2026-02.
"""

import os
from pathlib import Path
from typing import Optional, Any
from dotenv import load_dotenv
import structlog

log = structlog.get_logger("hive_commons.config")

# === PATHS ===
L1_ROOT = Path("D:/Proyectos/1midos")

# Knowledge paths
L1_KNOWLEDGE = L1_ROOT / "knowledge"
L1_MEMORY = L1_KNOWLEDGE / "memory"
LANCE_DB_URI = L1_MEMORY / "midos_knowledge.lance"

# Synapse (communication)
L1_SYNAPSE = L1_ROOT / "synapse"

# Logs
L1_LOGS = L1_ROOT / "logs"


def load_hive_env() -> dict:
    """
    Load environment variables from MidOS .env file.

    Returns dict with loaded source for debugging.
    """
    loaded = {}

    l1_env = L1_ROOT / ".env"
    if l1_env.exists():
        load_dotenv(l1_env, override=True)
        loaded["l1"] = str(l1_env)

    log.debug("hive_env_loaded", sources=loaded)
    return loaded


def get_api_key(key_name: str) -> Optional[str]:
    """
    Get an API key with fallback aliases.

    Example:
        get_api_key("GEMINI") -> checks GEMINI_API_KEY, GOOGLE_API_KEY
        get_api_key("OPENROUTER") -> checks OPENROUTER_API_KEY, OPENROUTER_KEY
    """
    aliases = {
        "GEMINI": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "OPENROUTER": ["OPENROUTER_API_KEY", "OPENROUTER_KEY"],
        "ANTHROPIC": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "OPENAI": ["OPENAI_API_KEY"],
    }

    key_name_upper = key_name.upper()
    candidates = aliases.get(key_name_upper, [f"{key_name_upper}_API_KEY", key_name_upper])

    for candidate in candidates:
        value = os.getenv(candidate)
        if value:
            return value

    return None


def get_gemini_keys() -> list[str]:
    """Get all available Gemini API keys for rotation."""
    keys = []
    for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
        key = os.getenv(var)
        if key and key not in keys:
            keys.append(key)
    return keys


# === BUDGET LIMITS ===
DAILY_BUDGET_USD = float(os.getenv("HIVE_DAILY_BUDGET", "5.0"))
WEEKLY_BUDGET_USD = float(os.getenv("HIVE_WEEKLY_BUDGET", "30.0"))


# === RESOURCE OPTIMIZATION (Lite Mode) ===
LITE_MODE = os.getenv("HIVE_LITE_MODE", "true").lower() == "true"

# Intervalos adaptativos (segundos)
INTERVALS = {
    "NORMAL": {
        "DASHBOARD_RERUN": 2,
        "PROACTIVE_WORKER": 60,
        "WATCHER_POLLING": 5,
        "HIVE_LOOP": 10
    },
    "LITE": {
        "DASHBOARD_RERUN": 15,    # Muy lento en idle
        "PROACTIVE_WORKER": 60,   # 1 min (Was 600s/10min) - "Always-On"
        "WATCHER_POLLING": 30,
        "HIVE_LOOP": 10           # 10s (Was 60s) - More responsive
    }

}

def get_interval(task_name: str) -> int:
    """Get interval based on current LITE_MODE."""
    mode = "LITE" if LITE_MODE else "NORMAL"
    return INTERVALS[mode].get(task_name, 60)

# === AUTO-LOAD ON IMPORT ===
# This ensures env is loaded when any hive_commons module is imported
_env_loaded = False

def ensure_env():
    global _env_loaded
    if not _env_loaded:
        load_hive_env()
        _env_loaded = True

def get_config(key: str, default: Optional[Any] = None) -> Any:
    """
    Get a configuration value from environment variables.
    Converts dot notation (llm.temp) to ENV notation (LLM_TEMP).
    """
    env_key = key.upper().replace(".", "_")
    val = os.getenv(env_key)
    if val is None:
        return default
    
    # Try to parse numeric types
    try:
        if "." in val: return float(val)
        return int(val)
    except (ValueError, TypeError):
        # Check booleans
        if val.lower() in ["true", "yes"]: return True
        if val.lower() in ["false", "no"]: return False
        return val

ensure_env()
