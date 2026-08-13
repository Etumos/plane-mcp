from unittest.mock import AsyncMock

import pytest

from plane_mcp.client import PlaneClient


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data
        self.content = b"{}" if json_data is not None else b""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


@pytest.mark.asyncio
async def test_get_calls_correct_url_and_returns_json(monkeypatch):
    client = PlaneClient(api_key="dummy", api_url="https://api.plane.so")

    captured = {}

    async def fake_request(method, url, json=None, params=None):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(200, {"results": [{"id": "1", "name": "Demo"}]})

    monkeypatch.setattr(client._client, "request", fake_request)

    result = await client.get(
        "/api/v1/workspaces/acme/projects/proj1/issues/", params={"per_page": 20}
    )

    assert captured["method"] == "GET"
    assert captured["url"] == "https://api.plane.so/api/v1/workspaces/acme/projects/proj1/issues/"
    assert captured["params"] == {"per_page": 20}
    assert result == {"results": [{"id": "1", "name": "Demo"}]}

    await client.aclose()


@pytest.mark.asyncio
async def test_delete_with_no_content_returns_none(monkeypatch):
    client = PlaneClient(api_key="dummy", api_url="https://api.plane.so")

    async def fake_request(method, url, json=None, params=None):
        return _FakeResponse(204, None)

    monkeypatch.setattr(client._client, "request", fake_request)

    result = await client.delete("/api/v1/workspaces/acme/projects/proj1/issues/issue1/")
    assert result is None

    await client.aclose()


@pytest.mark.asyncio
async def test_post_sends_json_body(monkeypatch):
    client = PlaneClient(api_key="dummy", api_url="https://api.plane.so")

    captured = {}

    async def fake_request(method, url, json=None, params=None):
        captured["json"] = json
        return _FakeResponse(201, {"id": "new-issue"})

    monkeypatch.setattr(client._client, "request", fake_request)

    result = await client.post(
        "/api/v1/workspaces/acme/projects/proj1/issues/", json={"name": "Bug"}
    )

    assert captured["json"] == {"name": "Bug"}
    assert result == {"id": "new-issue"}

    await client.aclose()
