"""
MIDOS MCP SERVER
================
Expone el knowledge base como herramientas MCP.
"""

from .midos_mcp import main as run_server

__all__ = ["run_server"]
