#!/usr/bin/env python3
"""plane-mcp — MCP server exposing the full Plane project-management API.

Runs over stdio by default (the transport MCP clients like Claude
Desktop and Cursor launch). Pass --http (or set PLANE_MCP_HTTP=1) to
run as a long-lived HTTP/SSE service instead, for self-hosting.

Tool descriptions, JSON schemas, and REST endpoint shapes live in
`plane_mcp.tools.TOOL_SPECS` — this module just wires that registry up
to the MCP protocol and dispatches calls through `PlaneClient`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from typing import Any

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from plane_mcp.client import PlaneClient
from plane_mcp.config import Config, ConfigError, fail_loud, load_config
from plane_mcp.tools import TOOL_SPECS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,  # never write logs to stdout: that's the stdio MCP channel
)
logger = logging.getLogger("plane_mcp")

server = Server("plane-mcp")

# Populated by main() before the server starts serving requests.
_config: Config | None = None
_client: PlaneClient | None = None

_PATH_PARAM_RE = re.compile(r"{(\w+)}")


def _path_params(path: str) -> list[str]:
    return _PATH_PARAM_RE.findall(path)


def _build_schema(spec: dict[str, Any]) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": spec.get("properties", {})}
    required = spec.get("required")
    if required:
        schema["required"] = required
    return schema


def validate_arguments(name: str, arguments: dict) -> tuple[bool, str]:
    """Validate arguments against the tool's JSON schema (required fields
    + basic type checks). Returns (ok, reason)."""
    spec = TOOL_SPECS.get(name)
    if spec is None:
        return False, f"Unknown tool: {name}"

    for field in spec.get("required", []):
        if field not in arguments or arguments[field] in (None, ""):
            return False, f"Missing required field: {field}"

    properties = spec.get("properties", {})
    type_map = {
        "string": str,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    for field, value in arguments.items():
        prop = properties.get(field)
        if prop is None:
            continue
        expected = type_map.get(prop.get("type"))
        # bool is a subclass of int in Python; only enforce when it matters
        if expected is int and isinstance(value, bool):
            return False, f"Field '{field}' must be an integer"
        if expected is not None and not isinstance(value, expected):
            return False, f"Field '{field}' must be of type {prop.get('type')}"

    return True, "OK"


def check_destructive_confirm(name: str, arguments: dict) -> tuple[bool, str]:
    """Guard destructive ops: require confirm=true AND a non-empty exact
    target id, named by the spec's `destructive` field. Returns (ok, reason)."""
    spec = TOOL_SPECS.get(name, {})
    target_field = spec.get("destructive")
    if target_field is None:
        return True, "OK"

    if arguments.get("confirm") is not True:
        return False, f"Destructive operation '{name}' requires confirm=true"

    target = arguments.get(target_field)
    if not target or not isinstance(target, str):
        return False, (
            f"Destructive operation '{name}' requires an explicit '{target_field}' target"
        )

    return True, "OK"


@server.list_tools()
async def list_tools() -> list[Tool]:
    assert _config is not None
    tools = []
    for tool_name, spec in TOOL_SPECS.items():
        if not _config.is_tool_enabled(tool_name):
            continue
        tools.append(
            Tool(
                name=tool_name,
                description=spec["description"],
                inputSchema=_build_schema(spec),
            )
        )
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    assert _config is not None
    arguments = arguments or {}

    if TOOL_SPECS.get(name) is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    if not _config.is_tool_enabled(name):
        return [TextContent(type="text", text=f"Tool disabled by PLANE_MCP_ENABLED_TOOLS: {name}")]

    ok, reason = validate_arguments(name, arguments)
    if not ok:
        logger.warning(f"Rejected call to {name}: {reason}")
        return [TextContent(type="text", text=f"Invalid arguments: {reason}")]

    confirmed, confirm_reason = check_destructive_confirm(name, arguments)
    if not confirmed:
        logger.warning(f"Destructive op blocked: {name} - {confirm_reason}")
        return [TextContent(type="text", text=f"Confirmation required: {confirm_reason}")]

    try:
        result = await execute_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:  # noqa: BLE001 — surface any failure back to the client
        logger.error(f"Tool execution failed: {name} - {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


async def execute_tool(name: str, arguments: dict) -> Any:
    """Dispatch a validated tool call through PlaneClient using its
    declarative spec from TOOL_SPECS."""
    assert _client is not None
    assert _config is not None

    spec = TOOL_SPECS[name]

    if spec.get("synthetic") == "list_workspaces":
        slug = arguments.get("workspace_slug") or _config.workspace_slug
        return await _client_synth_list_workspaces(slug)

    method = spec["method"]
    path_template = spec["path"]
    path_param_names = _path_params(path_template)

    missing_path_params = [p for p in path_param_names if p not in arguments]
    if missing_path_params:
        raise ValueError(f"Missing path argument(s): {', '.join(missing_path_params)}")
    path = path_template.format(**{p: arguments[p] for p in path_param_names})

    exclude = set(path_param_names) | {"confirm"}
    remaining = {k: v for k, v in arguments.items() if k not in exclude}

    if method == "GET":
        query_map = spec.get("query_map", {})
        params = {query_map.get(k, k): v for k, v in remaining.items()}
        return await _client.get(path, params=params or None)

    if method == "DELETE":
        query_map = spec.get("query_map", {})
        params = {query_map.get(k, k): v for k, v in remaining.items()}
        result = await _client.delete(path, params=params or None)
        if result is None:
            target_field = spec.get("destructive")
            result = {
                "status": "deleted",
                **({target_field: arguments[target_field]} if target_field else {}),
            }
        return result

    # POST / PATCH
    payload_map = spec.get("payload_map", {})
    payload: dict[str, Any] = dict(spec.get("static_payload", {}))
    for key, value in remaining.items():
        mapped_key = payload_map.get(key, key)
        if mapped_key is None:
            continue
        payload[mapped_key] = value

    if method == "POST":
        return await _client.post(path, json=payload)
    if method == "PATCH":
        return await _client.patch(path, json=payload)

    raise ValueError(f"Unsupported HTTP method '{method}' for tool '{name}'")


async def _client_synth_list_workspaces(workspace_slug: str | None) -> dict[str, Any]:
    """The Plane API key is scoped to a single workspace: there is no
    list-all endpoint, and the scoped key generally cannot read
    arbitrary workspace detail. Report the workspace the caller
    configured/asked for."""
    if not workspace_slug:
        return {"workspaces": []}
    return {"workspaces": [{"slug": workspace_slug}]}


async def run_stdio(config: Config) -> None:
    global _config, _client
    _config = config
    _client = PlaneClient(api_key=config.api_key, api_url=config.api_url)
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("plane-mcp server started (stdio)")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="plane-mcp",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    finally:
        await _client.aclose()


async def run_http(config: Config) -> None:
    """Run as a long-lived HTTP/SSE service for self-hosting.

    Requires the optional `http` extra (uvicorn + starlette):
        pip install 'plane-mcp[http]'
    """
    global _config, _client
    try:
        import uvicorn
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
    except ImportError as e:  # pragma: no cover
        fail_loud(
            "HTTP mode requires the 'http' extra. Install with:\n\n"
            "  pip install 'plane-mcp[http]'\n"
            f"\n(missing dependency: {e.name})"
        )
        return

    _config = config
    _client = PlaneClient(api_key=config.api_key, api_url=config.api_url)

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="plane-mcp",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    logger.info(f"plane-mcp server started (http) on {config.http_host}:{config.http_port}")
    try:
        uvicorn_config = uvicorn.Config(
            app, host=config.http_host, port=config.http_port, log_level="info"
        )
        server_instance = uvicorn.Server(uvicorn_config)
        await server_instance.serve()
    finally:
        await _client.aclose()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="plane-mcp",
        description="MCP server for the Plane project-management API.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run as an HTTP/SSE service instead of stdio (or set PLANE_MCP_HTTP=1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for HTTP mode (default 8000, or PLANE_MCP_PORT)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host for HTTP mode (default 127.0.0.1, or PLANE_MCP_HOST)",
    )
    return parser.parse_args(argv)


def cli() -> None:
    """Console-script entrypoint (`plane-mcp`)."""
    args = parse_args()

    try:
        config = load_config()
    except ConfigError as e:
        fail_loud(str(e))
        return

    if args.http:
        config.http_mode = True
    if args.port is not None:
        config.http_port = args.port
    if args.host is not None:
        config.http_host = args.host

    if config.http_mode:
        asyncio.run(run_http(config))
    else:
        asyncio.run(run_stdio(config))


if __name__ == "__main__":
    cli()
