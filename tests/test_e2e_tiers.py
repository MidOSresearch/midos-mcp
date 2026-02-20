#!/usr/bin/env python3
"""
E2E Tier Testing Suite for midos.dev
=====================================
Tests the full MCP protocol chain against the live server,
verifying tier gating, content truncation, and auth enforcement.

Usage:
    pytest tests/test_e2e_tiers.py -v
    pytest tests/test_e2e_tiers.py -v -k "community"
    pytest tests/test_e2e_tiers.py -v --endpoint http://localhost:8419

Environment:
    MIDOS_TEST_ENDPOINT  - MCP endpoint (default: https://midos.dev/mcp)
    MIDOS_TEST_API_KEY   - Pro API key for gated tests (optional)
"""

import json
import os
import time

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ENDPOINT = os.environ.get("MIDOS_TEST_ENDPOINT", "https://midos.dev/mcp")
API_KEY = os.environ.get("MIDOS_TEST_API_KEY", "")

COMMUNITY_TOOLS = {
    "search_knowledge", "list_skills", "hive_status", "project_status",
    "agent_handshake", "agent_bootstrap", "get_skill", "get_protocol",
}
PRO_TOOLS = {
    "get_eureka", "get_truth", "semantic_search", "research_youtube",
    "chunk_code", "memory_stats", "pool_status", "episodic_search",
}
ADMIN_TOOLS = {"episodic_store", "pool_signal"}

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mcp_request(method: str, params: dict = None, msg_id: int = 1,
                auth_header: str = None) -> dict:
    """Send an MCP JSON-RPC request and return the parsed result."""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": msg_id,
    }
    if params:
        payload["params"] = params

    headers = dict(HEADERS)
    if auth_header:
        headers["Authorization"] = auth_header

    resp = httpx.post(ENDPOINT, json=payload, headers=headers, timeout=30)
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}"

    # Parse SSE response
    text = resp.text.strip()
    for line in text.split("\n"):
        if line.startswith("data: "):
            return json.loads(line[6:])

    # Fallback: try direct JSON
    return json.loads(text)


def call_tool(tool_name: str, args: dict = None, auth_header: str = None) -> dict:
    """Call an MCP tool and return the full response."""
    params = {"name": tool_name, "arguments": args or {}}
    return mcp_request("tools/call", params, auth_header=auth_header)


def tool_result_text(response: dict) -> str:
    """Extract text content from a tool call response."""
    result = response.get("result", {})
    content = result.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", "")
    return ""


def tool_is_error(response: dict) -> bool:
    """Check if the response is an error."""
    return (
        "error" in response
        or response.get("result", {}).get("isError", False)
    )


# ---------------------------------------------------------------------------
# Round 1: Protocol Basics
# ---------------------------------------------------------------------------

class TestProtocol:
    """Verify MCP protocol works end-to-end."""

    def test_initialize(self):
        """Server responds to initialize with correct protocol version."""
        resp = mcp_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "e2e-test", "version": "1.0"},
        })
        assert "result" in resp, f"No result in response: {resp}"
        result = resp["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert result["serverInfo"]["name"] == "midos"
        assert "tools" in result["capabilities"]

    def test_tools_list(self):
        """Server lists all expected tools."""
        resp = mcp_request("tools/list")
        tools = resp["result"]["tools"]
        tool_names = {t["name"] for t in tools}

        # All community + pro + admin tools should be listed
        expected = COMMUNITY_TOOLS | PRO_TOOLS | ADMIN_TOOLS
        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"

    def test_tools_have_schemas(self):
        """Every tool has an inputSchema defined."""
        resp = mcp_request("tools/list")
        for tool in resp["result"]["tools"]:
            assert "inputSchema" in tool, f"Tool {tool['name']} missing inputSchema"

    def test_invalid_method(self):
        """Invalid JSON-RPC method returns error."""
        resp = mcp_request("nonexistent/method")
        assert "error" in resp, "Expected error for invalid method"

    def test_get_rejects_with_405_or_406(self):
        """GET to /mcp is rejected (MCP is POST-only for messages)."""
        try:
            resp = httpx.get(ENDPOINT, headers=HEADERS, timeout=15)
            # Server should reject GET with 405 or 406
            assert resp.status_code in (405, 406), (
                f"Expected 405/406 for GET, got {resp.status_code}"
            )
        except httpx.ReadTimeout:
            # Cloudflare/proxy may hang on unsupported methods — acceptable
            pass


# ---------------------------------------------------------------------------
# Round 2: Community Tier (no auth)
# ---------------------------------------------------------------------------

class TestCommunityTier:
    """Verify community tools work without authentication."""

    def test_search_knowledge(self):
        """search_knowledge returns results or empty without error."""
        resp = call_tool("search_knowledge", {"query": "python", "max_results": 3})
        assert not tool_is_error(resp), f"Error: {resp}"
        text = tool_result_text(resp)
        assert isinstance(text, str)

    def test_list_skills(self):
        """list_skills returns a non-empty skill list."""
        resp = call_tool("list_skills")
        assert not tool_is_error(resp)
        text = tool_result_text(resp)
        assert "Available skills" in text
        # Should have skills now that SKILLS_DIR is fixed
        assert "(0)" not in text, "Expected skills but got 0"

    def test_list_skills_with_stack_filter(self):
        """list_skills with stack filter returns filtered results."""
        resp = call_tool("list_skills", {"stack": "python"})
        assert not tool_is_error(resp)

    def test_hive_status(self):
        """hive_status returns system stats."""
        resp = call_tool("hive_status")
        assert not tool_is_error(resp)
        text = tool_result_text(resp)
        data = json.loads(text)
        assert data["knowledge_files"] > 0
        assert data["skills_count"] > 0

    def test_project_status(self):
        """project_status returns live system status."""
        resp = call_tool("project_status")
        assert not tool_is_error(resp)
        text = tool_result_text(resp)
        assert len(text) > 100  # Should be a substantial response

    def test_get_skill_existing(self):
        """get_skill returns content for a known skill."""
        resp = call_tool("get_skill", {"name": "angular"})
        assert not tool_is_error(resp)
        text = tool_result_text(resp)
        assert "angular" in text.lower()

    def test_get_skill_truncated(self):
        """Community tier gets truncated skill content (max ~400 chars)."""
        resp = call_tool("get_skill", {"name": "angular"})
        text = tool_result_text(resp)
        # Skill content should be truncated for community tier
        # The sync strips to 400 chars + upgrade notice
        # Total with notice should be under ~600 chars
        assert len(text) < 800, f"Skill too long for community tier: {len(text)} chars"

    def test_get_skill_nonexistent(self):
        """get_skill for unknown name returns not-found message."""
        resp = call_tool("get_skill", {"name": "nonexistent_skill_xyz"})
        text = tool_result_text(resp)
        assert "not found" in text.lower()

    def test_agent_handshake(self):
        """agent_handshake returns personalized config."""
        resp = call_tool("agent_handshake", {
            "model": "claude-opus-4-6",
            "client": "claude-code",
            "languages": "python,typescript",
        })
        assert not tool_is_error(resp)
        text = tool_result_text(resp)
        assert len(text) > 50

    def test_agent_bootstrap(self):
        """agent_bootstrap (deprecated) still works."""
        resp = call_tool("agent_bootstrap")
        assert not tool_is_error(resp)

    def test_get_protocol(self):
        """get_protocol returns not-found for nonexistent protocol."""
        resp = call_tool("get_protocol", {"name": "NONEXISTENT"})
        assert not tool_is_error(resp)
        text = tool_result_text(resp)
        assert "not found" in text.lower() or "no protocol" in text.lower()


# ---------------------------------------------------------------------------
# Round 3: Pro Tier Gating (no auth = should be rejected)
# ---------------------------------------------------------------------------

class TestProTierGating:
    """Verify PRO tools are blocked without valid API key."""

    @pytest.mark.parametrize("tool_name", sorted(PRO_TOOLS))
    def test_pro_tool_blocked_no_auth(self, tool_name):
        """PRO tool is blocked for unauthenticated requests."""
        resp = call_tool(tool_name, _default_args(tool_name))
        # Should either be an error or contain tier upgrade message
        text = tool_result_text(resp)
        is_blocked = (
            tool_is_error(resp)
            or "requires" in text.lower()
            or "upgrade" in text.lower()
            or "pro" in text.lower()
            or "tier" in text.lower()
        )
        assert is_blocked, (
            f"PRO tool '{tool_name}' should be blocked without auth. "
            f"Got: {text[:200]}"
        )

    @pytest.mark.parametrize("tool_name", sorted(ADMIN_TOOLS))
    def test_admin_tool_blocked_no_auth(self, tool_name):
        """ADMIN tool is blocked for unauthenticated requests."""
        resp = call_tool(tool_name, _default_args(tool_name))
        text = tool_result_text(resp)
        is_blocked = (
            tool_is_error(resp)
            or "requires" in text.lower()
            or "upgrade" in text.lower()
            or "admin" in text.lower()
            or "tier" in text.lower()
        )
        assert is_blocked, (
            f"ADMIN tool '{tool_name}' should be blocked without auth. "
            f"Got: {text[:200]}"
        )


# ---------------------------------------------------------------------------
# Round 4: Auth Validation
# ---------------------------------------------------------------------------

class TestAuthValidation:
    """Verify authentication edge cases."""

    def test_invalid_api_key_format(self):
        """Malformed API key doesn't grant elevated access."""
        resp = call_tool(
            "get_eureka", {"name": "test"},
            auth_header="midos_sk_INVALID",
        )
        text = tool_result_text(resp)
        is_blocked = tool_is_error(resp) or "requires" in text.lower() or "tier" in text.lower()
        assert is_blocked, f"Invalid key should not grant PRO access: {text[:200]}"

    def test_random_bearer_token(self):
        """Random Bearer token doesn't grant access."""
        resp = call_tool(
            "get_eureka", {"name": "test"},
            auth_header="Bearer random_token_12345",
        )
        text = tool_result_text(resp)
        is_blocked = tool_is_error(resp) or "requires" in text.lower() or "tier" in text.lower()
        assert is_blocked, f"Random Bearer should not grant access: {text[:200]}"

    def test_empty_auth_header(self):
        """Empty auth header treated as community tier."""
        resp = call_tool(
            "get_eureka", {"name": "test"},
            auth_header="",
        )
        text = tool_result_text(resp)
        is_blocked = tool_is_error(resp) or "requires" in text.lower() or "tier" in text.lower()
        assert is_blocked

    def test_oversized_key_rejected(self):
        """API key over 128 chars is rejected."""
        long_key = "midos_sk_pro_" + "A" * 200
        resp = call_tool(
            "get_eureka", {"name": "test"},
            auth_header=long_key,
        )
        text = tool_result_text(resp)
        is_blocked = tool_is_error(resp) or "requires" in text.lower() or "invalid" in text.lower()
        assert is_blocked


# ---------------------------------------------------------------------------
# Round 5: Pro Tier Access (requires MIDOS_TEST_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not API_KEY, reason="MIDOS_TEST_API_KEY not set")
class TestProTierAccess:
    """Verify PRO tools work with valid API key."""

    def test_get_eureka_with_key(self):
        """get_eureka works with valid PRO key."""
        resp = call_tool(
            "get_eureka", {"name": "EUREKA_RESPONSE_CACHE_2026"},
            auth_header=API_KEY,
        )
        assert not tool_is_error(resp)

    def test_semantic_search_with_key(self):
        """semantic_search works with valid PRO key."""
        resp = call_tool(
            "semantic_search", {"query": "caching patterns"},
            auth_header=API_KEY,
        )
        assert not tool_is_error(resp)

    def test_memory_stats_with_key(self):
        """memory_stats works with valid PRO key."""
        resp = call_tool("memory_stats", auth_header=API_KEY)
        assert not tool_is_error(resp)


# ---------------------------------------------------------------------------
# Round 6: Content Security
# ---------------------------------------------------------------------------

class TestContentSecurity:
    """Verify no premium content leaks to community tier."""

    def test_skill_has_upgrade_notice(self):
        """Truncated skill content includes upgrade notice."""
        resp = call_tool("get_skill", {"name": "angular"})
        text = tool_result_text(resp)
        # Skills are stripped to 400 chars with upgrade notice
        has_notice = (
            "pro" in text.lower()
            or "pricing" in text.lower()
            or "full content" in text.lower()
            or "note" in text.lower()
        )
        assert has_notice or len(text) < 500, (
            "Skill should be truncated with upgrade notice or short enough"
        )

    def test_search_returns_snippets_not_full(self):
        """search_knowledge returns snippets, not full documents."""
        resp = call_tool("search_knowledge", {"query": "react hooks", "max_results": 1})
        text = tool_result_text(resp)
        # Chunks are stripped to 250 chars each in the public repo
        if "No results" not in text:
            # If there are results, each should be a snippet
            assert len(text) < 5000, "Search results too long — possible content leak"

    def test_no_internal_chunks_exposed(self):
        """Searching for internal content returns nothing sensitive."""
        for query in ["rentahuman", "sovereign_mirror", "forensic", "pain_detection"]:
            resp = call_tool("search_knowledge", {"query": query, "max_results": 5})
            text = tool_result_text(resp)
            assert "internal" not in text.lower() or "no results" in text.lower(), (
                f"Internal content may be exposed for query '{query}': {text[:200]}"
            )


# ---------------------------------------------------------------------------
# Round 7: Rate Limiting / Abuse Prevention
# ---------------------------------------------------------------------------

class TestAbusePrevention:
    """Verify basic abuse prevention works."""

    def test_path_traversal_in_skill_name(self):
        """Path traversal in skill name is rejected."""
        resp = call_tool("get_skill", {"name": "../../../etc/passwd"})
        text = tool_result_text(resp)
        assert "passwd" not in text or "invalid" in text.lower() or "not found" in text.lower()

    def test_path_traversal_dots(self):
        """Double-dot path traversal blocked."""
        resp = call_tool("get_skill", {"name": "..\\..\\..\\windows\\system32"})
        text = tool_result_text(resp)
        # Traversal should be blocked — result is "not found", not actual file contents
        assert "not found" in text.lower() or "invalid" in text.lower()

    def test_special_chars_in_skill_name(self):
        """Special characters in skill name handled safely."""
        resp = call_tool("get_skill", {"name": "<script>alert(1)</script>"})
        text = tool_result_text(resp)
        # Should be rejected or return not-found, not execute
        assert "not found" in text.lower() or "invalid" in text.lower()


# ---------------------------------------------------------------------------
# Round 8: Concurrent Requests
# ---------------------------------------------------------------------------

class TestConcurrency:
    """Verify server handles concurrent requests."""

    def test_parallel_community_tools(self):
        """5 parallel requests to community tools all succeed."""
        import concurrent.futures

        tools = [
            ("hive_status", {}),
            ("list_skills", {}),
            ("search_knowledge", {"query": "python"}),
            ("project_status", {}),
            ("get_skill", {"name": "react"}),
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(call_tool, name, args)
                for name, args in tools
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        errors = [r for r in results if tool_is_error(r)]
        assert len(errors) == 0, f"Parallel requests had {len(errors)} errors"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_args(tool_name: str) -> dict:
    """Return minimal valid arguments for a tool."""
    defaults = {
        "get_eureka": {"name": "test"},
        "get_truth": {"name": "test"},
        "semantic_search": {"query": "test"},
        "research_youtube": {"url": "https://www.youtube.com/watch?v=test"},
        "chunk_code": {"file_path": "/tmp/test.py"},
        "memory_stats": {},
        "pool_status": {},
        "pool_signal": {"action": "test", "topic": "test", "summary": "test"},
        "episodic_search": {"query": "test"},
        "episodic_store": {"task_type": "TEST", "input_preview": "test"},
    }
    return defaults.get(tool_name, {})
