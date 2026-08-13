import os

import pytest

from plane_mcp.config import ConfigError, load_config


def test_missing_api_key_fails_loud(monkeypatch):
    monkeypatch.delenv("PLANE_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="PLANE_API_KEY"):
        load_config()


def test_defaults(monkeypatch):
    monkeypatch.setenv("PLANE_API_KEY", "dummy-token")
    monkeypatch.delenv("PLANE_API_URL", raising=False)
    monkeypatch.delenv("PLANE_WORKSPACE_SLUG", raising=False)
    monkeypatch.delenv("PLANE_MCP_ENABLED_TOOLS", raising=False)
    monkeypatch.delenv("PLANE_MCP_HTTP", raising=False)

    cfg = load_config()

    assert cfg.api_key == "dummy-token"
    assert cfg.api_url == "https://api.plane.so"
    assert cfg.workspace_slug is None
    assert cfg.enabled_tools is None
    assert cfg.http_mode is False
    assert cfg.is_tool_enabled("anything") is True  # permissive default


def test_self_hosted_api_url(monkeypatch):
    monkeypatch.setenv("PLANE_API_KEY", "dummy-token")
    monkeypatch.setenv("PLANE_API_URL", "https://plane.example.com/")
    cfg = load_config()
    assert cfg.api_url == "https://plane.example.com"


def test_enabled_tools_restricts(monkeypatch):
    monkeypatch.setenv("PLANE_API_KEY", "dummy-token")
    monkeypatch.setenv("PLANE_MCP_ENABLED_TOOLS", "list_issues, get_issue")
    cfg = load_config()
    assert cfg.enabled_tools == {"list_issues", "get_issue"}
    assert cfg.is_tool_enabled("list_issues") is True
    assert cfg.is_tool_enabled("delete_issue") is False


def test_http_mode_from_env(monkeypatch):
    monkeypatch.setenv("PLANE_API_KEY", "dummy-token")
    monkeypatch.setenv("PLANE_MCP_HTTP", "1")
    monkeypatch.setenv("PLANE_MCP_PORT", "9001")
    cfg = load_config()
    assert cfg.http_mode is True
    assert cfg.http_port == 9001
