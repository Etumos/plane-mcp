"""Environment-variable configuration for plane-mcp.

No config file is required. Everything is read from the process
environment, which is how MCP clients (Claude Desktop, Cursor, etc.)
pass configuration to stdio servers via their `env` block.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field


DEFAULT_API_URL = "https://api.plane.so"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass
class Config:
    api_key: str
    api_url: str = DEFAULT_API_URL
    workspace_slug: str | None = None
    enabled_tools: set[str] | None = field(default=None)
    http_mode: bool = False
    http_host: str = "127.0.0.1"
    http_port: int = 8000

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Permissive by default: every tool is enabled unless the user
        explicitly restricts the set via PLANE_MCP_ENABLED_TOOLS."""
        if self.enabled_tools is None:
            return True
        return tool_name in self.enabled_tools


def _parse_enabled_tools(raw: str | None) -> set[str] | None:
    if raw is None or raw.strip() == "":
        return None
    return {t.strip() for t in raw.split(",") if t.strip()}


def load_config(argv: list[str] | None = None) -> Config:
    """Build a Config from environment variables (+ optional CLI flags
    handled by server.py for --http/--port, which override the env)."""
    api_key = os.environ.get("PLANE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "PLANE_API_KEY is not set. plane-mcp requires a Plane API token.\n"
            "Get one from your Plane instance under "
            "Workspace Settings -> API Tokens, then set it as an environment "
            "variable, e.g.:\n\n"
            "  export PLANE_API_KEY=plane_api_xxxxxxxx\n\n"
            "or add it to the `env` block of your MCP client config."
        )

    api_url = os.environ.get("PLANE_API_URL", DEFAULT_API_URL).strip().rstrip("/")
    if not api_url:
        api_url = DEFAULT_API_URL

    workspace_slug = os.environ.get("PLANE_WORKSPACE_SLUG", "").strip() or None

    enabled_tools = _parse_enabled_tools(os.environ.get("PLANE_MCP_ENABLED_TOOLS"))

    http_mode = os.environ.get("PLANE_MCP_HTTP", "").strip().lower() in ("1", "true", "yes")
    http_host = os.environ.get("PLANE_MCP_HOST", "127.0.0.1").strip() or "127.0.0.1"
    try:
        http_port = int(os.environ.get("PLANE_MCP_PORT", "8000"))
    except ValueError:
        http_port = 8000

    return Config(
        api_key=api_key,
        api_url=api_url,
        workspace_slug=workspace_slug,
        enabled_tools=enabled_tools,
        http_mode=http_mode,
        http_host=http_host,
        http_port=http_port,
    )


def fail_loud(message: str) -> None:
    """Print a clear error to stderr and exit non-zero."""
    print(f"plane-mcp: {message}", file=sys.stderr)
    sys.exit(1)
