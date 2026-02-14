"""
MidOS API Key Authentication + Rate Limiting Middleware for FastMCP.

Implements freemium tier gating:
  - No key → free tier (5 basic tools, 100 queries/mo)
  - Valid key → tier-based access (dev/pro/team → all tools)
  - Invalid key → 401 error on premium tools

Rate limits per tier:
  - free: 100 queries/month
  - dev:  5,000 queries/month
  - pro:  25,000 queries/month
  - team: 100,000 queries/month

Keys stored in config/api_keys.json, usage in config/api_usage.json.
"""

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.tool import Tool, ToolResult

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

FREE_TOOLS = {
    "search_knowledge",
    "list_skills",
    "hive_status",
    "project_status",
    "pool_status",
    "get_eureka",
    "get_truth",
}

# All tools not in FREE_TOOLS require a paid key.
# No need to enumerate — anything outside FREE_TOOLS is premium.

TIER_LIMITS = {
    "free": {"queries_per_month": 100},
    "dev":  {"queries_per_month": 5_000},
    "pro":  {"queries_per_month": 25_000},
    "team": {"queries_per_month": 100_000},
}

# ---------------------------------------------------------------------------
# Key storage
# ---------------------------------------------------------------------------

KEYS_FILE = Path(__file__).parent.parent.parent / "config" / "api_keys.json"
USAGE_FILE = Path(__file__).parent.parent.parent / "config" / "api_usage.json"


# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------

def _current_month() -> str:
    """Return current month as 'YYYY-MM' string."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_usage() -> dict[str, dict[str, Any]]:
    """Load usage data. Returns {identifier: {month: str, count: int}}."""
    if not USAGE_FILE.exists():
        return {}
    try:
        return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_usage(usage: dict[str, dict[str, Any]]) -> None:
    """Persist usage data to disk."""
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(
        json.dumps(usage, indent=2, default=str),
        encoding="utf-8",
    )


def _get_usage_count(identifier: str) -> int:
    """Get current month's query count for an identifier (key or IP hash)."""
    usage = _load_usage()
    entry = usage.get(identifier, {})
    if entry.get("month") == _current_month():
        return entry.get("count", 0)
    return 0


def _increment_usage(identifier: str) -> int:
    """Increment query count. Returns new count. Resets on new month."""
    usage = _load_usage()
    month = _current_month()
    entry = usage.get(identifier, {})

    if entry.get("month") != month:
        entry = {"month": month, "count": 0}

    entry["count"] = entry.get("count", 0) + 1
    usage[identifier] = entry
    _save_usage(usage)
    return entry["count"]


def get_usage_stats() -> list[dict[str, Any]]:
    """Get usage stats for all identifiers this month."""
    usage = _load_usage()
    month = _current_month()
    return [
        {"identifier": k[:16] + "...", "month": v.get("month"), "count": v.get("count", 0)}
        for k, v in usage.items()
        if v.get("month") == month
    ]


def _load_keys() -> dict[str, dict[str, Any]]:
    """Load API keys from disk. Returns {key_string: {tier, name, created, ...}}."""
    if not KEYS_FILE.exists():
        return {}
    try:
        return json.loads(KEYS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_keys(keys: dict[str, dict[str, Any]]) -> None:
    """Persist API keys to disk."""
    KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEYS_FILE.write_text(
        json.dumps(keys, indent=2, default=str),
        encoding="utf-8",
    )


def generate_key(name: str, tier: str = "dev") -> str:
    """Generate a new API key and save it.

    Returns the key string (midos_sk_...).
    """
    if tier not in TIER_LIMITS:
        raise ValueError(f"Invalid tier: {tier}. Must be one of {list(TIER_LIMITS)}")

    key = f"midos_sk_{secrets.token_hex(24)}"
    keys = _load_keys()
    keys[key] = {
        "name": name,
        "tier": tier,
        "created": datetime.now(timezone.utc).isoformat(),
        "active": True,
    }
    _save_keys(keys)
    return key


def revoke_key(key: str) -> bool:
    """Revoke an API key. Returns True if found and revoked."""
    keys = _load_keys()
    if key in keys:
        keys[key]["active"] = False
        keys[key]["revoked_at"] = datetime.now(timezone.utc).isoformat()
        _save_keys(keys)
        return True
    return False


def list_keys() -> list[dict[str, Any]]:
    """List all API keys (masked) with metadata."""
    keys = _load_keys()
    result = []
    for k, v in keys.items():
        result.append({
            "key_prefix": k[:16] + "...",
            "name": v.get("name", ""),
            "tier": v.get("tier", "free"),
            "active": v.get("active", True),
            "created": v.get("created", ""),
        })
    return result


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class ApiKeyMiddleware(Middleware):
    """FastMCP middleware that gates tools by API key tier.

    - Unauthenticated requests can only use FREE_TOOLS.
    - Authenticated requests get full access based on tier.
    - Invalid keys get a clear error on premium tool calls.
    """

    def __init__(self) -> None:
        import time
        self._keys_cache: dict[str, dict[str, Any]] | None = None
        self._cache_time: float = 0
        # In-memory usage counters (flushed to disk periodically)
        self._usage_mem: dict[str, int] = {}
        self._usage_month: str = _current_month()
        self._usage_flush_time: float = time.time()

    def _get_keys(self) -> dict[str, dict[str, Any]]:
        """Load keys with simple in-memory cache (reload every 60s)."""
        import time
        now = time.time()
        if self._keys_cache is None or (now - self._cache_time) > 60:
            self._keys_cache = _load_keys()
            self._cache_time = now
        return self._keys_cache

    def _check_and_increment(self, identifier: str, tier: str) -> tuple[bool, int, int]:
        """Check rate limit and increment counter.

        Returns (allowed, current_count, limit).
        Uses in-memory counter with periodic disk flush (every 30s).
        """
        import time

        limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])["queries_per_month"]
        month = _current_month()

        # Reset on new month
        if month != self._usage_month:
            self._usage_mem.clear()
            self._usage_month = month

        # Load from disk if not in memory
        if identifier not in self._usage_mem:
            self._usage_mem[identifier] = _get_usage_count(identifier)

        count = self._usage_mem[identifier]

        if count >= limit:
            return False, count, limit

        # Increment in memory
        self._usage_mem[identifier] = count + 1

        # Flush to disk every 30 seconds
        now = time.time()
        if (now - self._usage_flush_time) > 30:
            self._flush_usage()
            self._usage_flush_time = now

        return True, count + 1, limit

    def _flush_usage(self) -> None:
        """Write in-memory usage counters to disk."""
        usage = _load_usage()
        month = _current_month()
        for identifier, count in self._usage_mem.items():
            usage[identifier] = {"month": month, "count": count}
        _save_usage(usage)

    def _is_localhost(self) -> bool:
        """Check if the request originates from localhost."""
        try:
            headers = get_http_headers(include_all=True)
        except Exception:
            return False
        # Check standard proxy headers first, then fall back to host
        forwarded = headers.get("x-forwarded-for", "").split(",")[0].strip()
        real_ip = headers.get("x-real-ip", "")
        host = headers.get("host", "")
        local_addrs = {"127.0.0.1", "::1", "localhost"}
        if forwarded and forwarded in local_addrs:
            return True
        if real_ip and real_ip in local_addrs:
            return True
        # No proxy headers → check host (direct connection)
        host_name = host.split(":")[0] if host else ""
        if host_name in local_addrs:
            return True
        return False

    def _resolve_tier(self) -> tuple[str, str | None]:
        """Extract API key from headers and resolve tier.

        Localhost connections get full 'pro' access without a key.
        Returns (tier, key_or_none).
        """
        # Localhost bypass — full access for local development
        if self._is_localhost():
            return "pro", None

        headers = get_http_headers(include_all=True)
        auth_header = headers.get("authorization", "")

        if not auth_header:
            return "free", None

        # Expect "Bearer midos_sk_..."
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return "free", None

        token = parts[1].strip()
        if not token.startswith("midos_sk_"):
            return "free", None

        keys = self._get_keys()
        key_info = keys.get(token)

        if not key_info or not key_info.get("active", False):
            return "invalid", token

        return key_info.get("tier", "dev"), token

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next,
    ) -> ToolResult:
        """Gate tool execution by tier + rate limit."""
        tool_name = context.message.name
        tier, key = self._resolve_tier()

        # Invalid key — reject immediately
        if tier == "invalid":
            raise ToolError(
                f"Invalid or revoked API key. "
                f"Get a key at https://midos.dev/keys"
            )

        # No key + premium tool — reject
        if tool_name not in FREE_TOOLS and tier == "free" and key is None:
            raise ToolError(
                f"'{tool_name}' requires an API key. "
                f"Free tools: {', '.join(sorted(FREE_TOOLS))}. "
                f"Get a key at https://midos.dev/keys"
            )

        # Rate limit check (applies to ALL tool calls, free and premium)
        identifier = key if key else self._get_anonymous_id()
        allowed, count, limit = self._check_and_increment(identifier, tier)

        if not allowed:
            raise ToolError(
                f"Rate limit exceeded: {count}/{limit} queries this month. "
                f"Upgrade your tier at https://midos.dev/pricing"
            )

        return await call_next(context)

    def _get_anonymous_id(self) -> str:
        """Get a stable identifier for unauthenticated requests."""
        import hashlib
        headers = get_http_headers(include_all=True)
        # Use a hash of forwarded IP or fallback to "anonymous"
        ip = headers.get("x-forwarded-for", headers.get("x-real-ip", "anonymous"))
        return f"anon_{hashlib.sha256(ip.encode()).hexdigest()[:16]}"

    async def on_list_tools(
        self,
        context: MiddlewareContext,
        call_next,
    ) -> Sequence[Tool]:
        """Filter visible tools based on auth tier."""
        all_tools = await call_next(context)
        tier, _ = self._resolve_tier()

        if tier in ("dev", "pro", "team"):
            return all_tools

        # Free/unauthenticated: show all tools but mark premium ones
        # (we show all for discoverability, gating happens on call)
        return all_tools


# ---------------------------------------------------------------------------
# CLI for key management
# ---------------------------------------------------------------------------

def _cli():
    """Simple CLI for API key management.

    Usage:
        python -m modules.mcp_server.auth generate --name "my-app" --tier dev
        python -m modules.mcp_server.auth list
        python -m modules.mcp_server.auth revoke --key midos_sk_...
    """
    import argparse

    parser = argparse.ArgumentParser(description="MidOS API Key Management")
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="Generate a new API key")
    gen.add_argument("--name", required=True, help="Key name/description")
    gen.add_argument("--tier", default="dev", choices=list(TIER_LIMITS.keys()))

    sub.add_parser("list", help="List all API keys")

    rev = sub.add_parser("revoke", help="Revoke an API key")
    rev.add_argument("--key", required=True, help="Full key string to revoke")

    sub.add_parser("usage", help="Show usage stats for current month")

    args = parser.parse_args()

    if args.command == "generate":
        key = generate_key(args.name, args.tier)
        print(f"Generated {args.tier} key for '{args.name}':")
        print(f"  {key}")
        print(f"  Store this securely — it won't be shown again in full.")

    elif args.command == "list":
        keys = list_keys()
        if not keys:
            print("No API keys found.")
        else:
            print(f"{'Prefix':<22} {'Name':<20} {'Tier':<8} {'Active':<8} {'Created'}")
            print("-" * 80)
            for k in keys:
                print(f"{k['key_prefix']:<22} {k['name']:<20} {k['tier']:<8} "
                      f"{'yes' if k['active'] else 'NO':<8} {k['created'][:10]}")

    elif args.command == "revoke":
        if revoke_key(args.key):
            print(f"Key revoked: {args.key[:16]}...")
        else:
            print(f"Key not found: {args.key[:16]}...")

    elif args.command == "usage":
        stats = get_usage_stats()
        if not stats:
            print(f"No usage data for {_current_month()}.")
        else:
            print(f"Usage for {_current_month()}:")
            print(f"{'Identifier':<22} {'Queries':<10}")
            print("-" * 35)
            for s in stats:
                print(f"{s['identifier']:<22} {s['count']:<10}")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
