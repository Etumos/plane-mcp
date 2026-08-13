from unittest.mock import AsyncMock

import pytest

from plane_mcp import server
from plane_mcp.config import Config
from plane_mcp.tools import TOOL_SPECS


@pytest.fixture
def config():
    return Config(api_key="dummy", api_url="https://api.plane.so", workspace_slug="acme")


@pytest.mark.asyncio
async def test_list_tools_registers_full_surface(config, monkeypatch):
    monkeypatch.setattr(server, "_config", config)
    tools = await server.list_tools()
    names = {t.name for t in tools}

    assert len(tools) == len(TOOL_SPECS)
    for expected in (
        "list_workspaces",
        "list_projects",
        "create_issue",
        "list_cycles",
        "create_module",
        "list_pages",
        "create_webhook",
    ):
        assert expected in names


@pytest.mark.asyncio
async def test_list_tools_respects_enabled_tools_restriction(monkeypatch):
    cfg = Config(api_key="dummy", enabled_tools={"list_issues", "get_issue"})
    monkeypatch.setattr(server, "_config", cfg)
    tools = await server.list_tools()
    assert {t.name for t in tools} == {"list_issues", "get_issue"}


def test_validate_arguments_missing_required_field():
    ok, reason = server.validate_arguments("create_issue", {"workspace_slug": "acme"})
    assert ok is False
    assert "project_id" in reason


def test_validate_arguments_wrong_type():
    ok, reason = server.validate_arguments(
        "list_issues",
        {"workspace_slug": "acme", "project_id": "p1", "page_size": "not-an-int"},
    )
    assert ok is False
    assert "page_size" in reason


def test_validate_arguments_ok():
    ok, reason = server.validate_arguments(
        "create_issue", {"workspace_slug": "acme", "project_id": "p1", "title": "Bug"}
    )
    assert ok is True


def test_destructive_op_requires_confirm():
    ok, reason = server.check_destructive_confirm(
        "delete_issue", {"workspace_slug": "acme", "project_id": "p1", "issue_id": "i1"}
    )
    assert ok is False
    assert "confirm" in reason.lower()


def test_destructive_op_with_confirm_and_target_passes():
    ok, _ = server.check_destructive_confirm(
        "delete_issue",
        {"workspace_slug": "acme", "project_id": "p1", "issue_id": "i1", "confirm": True},
    )
    assert ok is True


def test_non_destructive_op_ignores_confirm():
    ok, _ = server.check_destructive_confirm(
        "create_issue", {"workspace_slug": "acme", "project_id": "p1", "title": "Bug"}
    )
    assert ok is True


@pytest.mark.asyncio
async def test_execute_tool_create_issue_builds_correct_call(config, monkeypatch):
    monkeypatch.setattr(server, "_config", config)
    fake_client = AsyncMock()
    fake_client.post.return_value = {"id": "issue-1", "name": "Bug"}
    monkeypatch.setattr(server, "_client", fake_client)

    result = await server.execute_tool(
        "create_issue",
        {"workspace_slug": "acme", "project_id": "proj1", "title": "Bug", "priority": "high"},
    )

    fake_client.post.assert_awaited_once_with(
        "/api/v1/workspaces/acme/projects/proj1/issues/",
        json={"name": "Bug", "priority": "high"},
    )
    assert result == {"id": "issue-1", "name": "Bug"}


@pytest.mark.asyncio
async def test_execute_tool_list_workspaces_is_synthetic(config, monkeypatch):
    monkeypatch.setattr(server, "_config", config)
    fake_client = AsyncMock()
    monkeypatch.setattr(server, "_client", fake_client)

    result = await server.execute_tool("list_workspaces", {})

    fake_client.get.assert_not_called()
    assert result == {"workspaces": [{"slug": "acme"}]}


@pytest.mark.asyncio
async def test_execute_tool_delete_issue_maps_path_params(config, monkeypatch):
    monkeypatch.setattr(server, "_config", config)
    fake_client = AsyncMock()
    fake_client.delete.return_value = None
    monkeypatch.setattr(server, "_client", fake_client)

    result = await server.execute_tool(
        "delete_issue", {"workspace_slug": "acme", "project_id": "p1", "issue_id": "i1"}
    )

    fake_client.delete.assert_awaited_once_with(
        "/api/v1/workspaces/acme/projects/p1/issues/i1/", params=None
    )
    assert result == {"status": "deleted", "issue_id": "i1"}


@pytest.mark.asyncio
async def test_call_tool_blocks_destructive_without_confirm(config, monkeypatch):
    monkeypatch.setattr(server, "_config", config)
    fake_client = AsyncMock()
    monkeypatch.setattr(server, "_client", fake_client)

    result = await server.call_tool(
        "delete_project", {"workspace_slug": "acme", "project_id": "p1"}
    )

    assert len(result) == 1
    assert "Confirmation required" in result[0].text
    fake_client.delete.assert_not_called()
