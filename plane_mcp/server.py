#!/usr/bin/env python3
"""plane-project-mcp — MCP server exposing the full Plane project-management API.

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

server = Server("plane-project-mcp")

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

    synthetic = spec.get("synthetic")
    if synthetic == "list_workspaces":
        slug = arguments.get("workspace_slug") or _config.workspace_slug
        return await _client_synth_list_workspaces(slug)
    if synthetic == "list_sub_issues":
        return await _client_synth_list_sub_issues(
            arguments["workspace_slug"], arguments["project_id"], arguments["issue_id"]
        )
    if synthetic == "create_intake_issue":
        return await _client_synth_create_intake_issue(arguments)
    if synthetic == "update_intake_issue":
        return await _client_synth_update_intake_issue(arguments)

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
    list_wrap = spec.get("list_wrap_payload", ())
    payload: dict[str, Any] = dict(spec.get("static_payload", {}))
    for key, value in remaining.items():
        mapped_key = payload_map.get(key, key)
        if mapped_key is None:
            continue
        if mapped_key in list_wrap and not isinstance(value, list):
            value = [value]
        payload[mapped_key] = value

    if method == "POST":
        return await _client.post(path, json=payload)
    if method == "PATCH":
        return await _client.patch(path, json=payload)

    raise ValueError(f"Unsupported HTTP method '{method}' for tool '{name}'")


async def _client_synth_list_workspaces(workspace_slug: str | None) -> dict[str, Any]:
    """List accessible workspaces.

    If a workspace slug is configured/passed, short-circuit without a live
    call: the Plane API key is scoped to a single workspace, so there's
    nothing more to discover and the scoped key generally can't read
    arbitrary workspace detail anyway. Otherwise, call the real
    GET /api/v1/workspaces/ endpoint.
    """
    if workspace_slug:
        return {"workspaces": [{"slug": workspace_slug}]}
    assert _client is not None
    result = await _client.get("/api/v1/workspaces/")
    workspaces = result if isinstance(result, list) else (result or {}).get("results", [])
    return {
        "workspaces": [
            {
                "id": w.get("id"),
                "name": w.get("name"),
                "slug": w.get("slug"),
                "created_at": w.get("created_at"),
                "owner": w.get("owner"),
            }
            for w in (workspaces if isinstance(workspaces, list) else [])
        ]
    }


_SUB_ISSUES_MAX_PAGES = 20  # 20 * 100 = 2000 issues scanned before giving up


async def _client_synth_list_sub_issues(
    workspace_slug: str, project_id: str, issue_id: str
) -> dict[str, Any]:
    """List the sub-issues (children) of an issue.

    There is no dedicated sub-issues endpoint and the server-side ?parent=
    filter is a confirmed no-op, so this paginates the project's issues and
    filters client-side on `parent == issue_id`. Scans up to 2000 issues
    (20 pages of 100); if the project has more than that, `truncated` is
    set True and not all sub-issues may be listed.
    """
    assert _client is not None
    path = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/"
    children: list[dict[str, Any]] = []
    truncated = True
    for page in range(1, _SUB_ISSUES_MAX_PAGES + 1):
        result = await _client.get(path, params={"page": page, "per_page": 100})
        rows = result if isinstance(result, list) else (result or {}).get("results", [])
        if not isinstance(rows, list):
            rows = []
        for row in rows:
            if row.get("parent") == issue_id:
                children.append(
                    {
                        "id": row.get("id"),
                        "name": row.get("name"),
                        "sequence_id": row.get("sequence_id"),
                        "state": row.get("state"),
                        "priority": row.get("priority"),
                    }
                )
        has_more = result.get("next_page_results") if isinstance(result, dict) else False
        if not has_more or not rows:
            truncated = False
            break
    return {
        "parent_issue_id": issue_id,
        "sub_issues": children,
        "count": len(children),
        "truncated": truncated,
    }


async def _client_synth_create_intake_issue(arguments: dict) -> Any:
    """Create an intake (inbox) issue.

    Verified: POST .../inbox-issues/ body {"issue": {name, description_html}}
    — the work-item fields are nested under an "issue" key, unlike
    list_issues/create_issue.
    """
    assert _client is not None
    workspace_slug = arguments["workspace_slug"]
    project_id = arguments["project_id"]
    issue_body: dict[str, Any] = {"name": arguments["title"]}
    if arguments.get("description"):
        issue_body["description_html"] = arguments["description"]
    path = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/inbox-issues/"
    return await _client.post(path, json={"issue": issue_body})


async def _client_synth_update_intake_issue(arguments: dict) -> Any:
    """Update an intake (inbox) issue's title/description.

    Verified: PATCH .../inbox-issues/{issue_id} body {"issue": {...}}
    (note: no trailing slash on the detail route).
    """
    assert _client is not None
    workspace_slug = arguments["workspace_slug"]
    project_id = arguments["project_id"]
    intake_issue_id = arguments["intake_issue_id"]
    issue_body: dict[str, Any] = {}
    if arguments.get("title"):
        issue_body["name"] = arguments["title"]
    if arguments.get("description"):
        issue_body["description_html"] = arguments["description"]
    if not issue_body:
        raise ValueError("at least one of title/description is required")
    path = f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/inbox-issues/{intake_issue_id}"
    return await _client.patch(path, json={"issue": issue_body})


async def run_stdio(config: Config) -> None:
    global _config, _client
    _config = config
    _client = PlaneClient(api_key=config.api_key, api_url=config.api_url)
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("plane-project-mcp server started (stdio)")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="plane-project-mcp",
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
        pip install 'plane-project-mcp[http]'
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
            "  pip install 'plane-project-mcp[http]'\n"
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
                    server_name="plane-project-mcp",
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

    logger.info(f"plane-project-mcp server started (http) on {config.http_host}:{config.http_port}")
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
        prog="plane-project-mcp",
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
    """Console-script entrypoint (`plane-project-mcp`)."""
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
