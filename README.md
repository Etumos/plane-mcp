# plane-project-mcp

An [MCP](https://modelcontextprotocol.io) server for [Plane](https://plane.so) —
the open-source project management tool. Point it at your own Plane
workspace (cloud or self-hosted) and let any MCP-compatible client
(Claude Desktop, Cursor, etc.) list, create, and update your projects,
issues, cycles, modules, labels, states, comments, pages, views, and
more.

You run it, you hold your own Plane
API token, it talks straight to the Plane REST API.

## Install

Pick one:

```bash
# Run without installing (recommended for MCP client use)
uvx plane-project-mcp

# or
pipx run plane-project-mcp

# or install into your environment
pip install plane-project-mcp
```

## Configuration

> **Self-hosted Plane users MUST set `PLANE_API_URL`** to their instance
> (e.g. `https://plane.yourcompany.com`). It defaults to
> `https://api.plane.so` (Plane Cloud), so if you don't set it, the server
> talks to Plane Cloud rather than your own deployment.

Everything is configured via environment variables — there is no
config file.

| Variable | Required | Default | Description |
|---|---|---|---|
| `PLANE_API_KEY` | yes | — | Your Plane API token |
| `PLANE_API_URL` | no | `https://api.plane.so` | Plane API base URL — point this at your self-hosted instance |
| `PLANE_WORKSPACE_SLUG` | no | — | Default workspace slug (used by `list_workspaces` when no slug is passed) |
| `PLANE_MCP_ENABLED_TOOLS` | no | *(all tools enabled)* | Comma-separated allowlist of tool names to expose |
| `PLANE_MCP_HTTP` | no | `0` | Set to `1` to run as an HTTP/SSE service instead of stdio |
| `PLANE_MCP_HOST` | no | `127.0.0.1` | Bind host in HTTP mode |
| `PLANE_MCP_PORT` | no | `8000` | Bind port in HTTP mode |

If `PLANE_API_KEY` is missing, the server fails immediately with a
clear error instead of starting half-configured.

### Getting a Plane API token

In Plane, go to **Workspace Settings -> API Tokens -> Add API token**,
give it a name, and copy the value. Treat it like a password — anyone
holding it can act as your workspace via this server's tools.

## Using it with an MCP client

`plane-project-mcp` speaks **stdio** by default, which is the transport MCP
clients launch as a subprocess.

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "plane": {
      "command": "uvx",
      "args": ["plane-project-mcp"],
      "env": {
        "PLANE_API_KEY": "your-plane-api-token",
        "PLANE_WORKSPACE_SLUG": "your-workspace-slug"
      }
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "plane": {
      "command": "uvx",
      "args": ["plane-project-mcp"],
      "env": {
        "PLANE_API_KEY": "your-plane-api-token",
        "PLANE_WORKSPACE_SLUG": "your-workspace-slug"
      }
    }
  }
}
```

### Generic `.mcp.json`

Most MCP-capable clients accept the same stdio shape:

```json
{
  "mcpServers": {
    "plane": {
      "command": "python",
      "args": ["-m", "plane_mcp.server"],
      "env": {
        "PLANE_API_KEY": "your-plane-api-token",
        "PLANE_API_URL": "https://api.plane.so",
        "PLANE_WORKSPACE_SLUG": "your-workspace-slug"
      }
    }
  }
}
```

Swap `command`/`args` for `pip install plane-project-mcp` + `["-m", "plane_mcp.server"]`,
or `uvx`/`pipx run` + `["plane-project-mcp"]` — whichever fits how you installed it.

## Self-hosting as an HTTP/SSE service

If you'd rather run `plane-project-mcp` as a long-lived service (e.g. behind a
reverse proxy) instead of launching it per-client, use `--http`:

```bash
pip install 'plane-project-mcp[http]'
PLANE_API_KEY=... plane-project-mcp --http --host 0.0.0.0 --port 8000
```

This serves an SSE endpoint at `/sse` (and `/messages/` for posting
client messages), which any MCP client with SSE transport support can
connect to.

### Docker

```bash
docker build -t plane-project-mcp .
docker run --rm -e PLANE_API_KEY=your-plane-api-token -p 8000:8000 plane-project-mcp
```

Or with Compose:

```bash
cp .env.example .env   # fill in PLANE_API_KEY
docker compose up
```

The bundled `docker-compose.yml` runs `plane-project-mcp --http` on port 8000.

## Available tools

`plane-project-mcp` covers the Plane REST API surface: workspaces, projects,
project members, issues (create/read/update/delete, comments,
attachments, links, relations, sub-issues, activity), labels, states,
cycles (+ cycle-issue membership, transfers), modules (+ module-issue
membership), pages, project views, workspace views, intake/inbox
issues, estimates, and webhooks.

By default every tool is enabled. To restrict a deployment to a subset
(e.g. read-only, or issues-only), set `PLANE_MCP_ENABLED_TOOLS` to a
comma-separated list of tool names, for example:

```bash
export PLANE_MCP_ENABLED_TOOLS=list_projects,list_issues,get_issue,create_issue,update_issue
```

Destructive operations (`delete_*`, `remove_*`) always require an
explicit `confirm: true` argument alongside the exact target ID —
there is no "delete everything" shortcut.

## Development

```bash
git clone https://github.com/Etumos/plane-project-mcp
cd plane-project-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,http]"
python -m pytest
```

Smoke-test the server locally (uses a dummy token, makes no network calls):

```bash
PLANE_API_KEY=dummy python -m plane_mcp.server --help
```

## License

MIT — see [LICENSE](LICENSE).
