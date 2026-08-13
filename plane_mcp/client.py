"""Thin async client around the Plane REST API.

Docs: https://developers.plane.so/api-reference/introduction

This client is deliberately generic: it exposes get/post/patch/delete
against the Plane API's base URL + auth header, and the resource-shaped
endpoint knowledge (URL templates, payload shape) lives in
`plane_mcp.tools.TOOL_SPECS` so the full Plane surface (projects,
issues, cycles, modules, labels, states, comments, attachments, links,
relations, pages, views, workspace-views, members, intake, estimates,
webhooks) can be described declaratively instead of one bespoke method
per endpoint.
"""

from __future__ import annotations

from typing import Any

import httpx


class PlaneClient:
    """Wraps httpx.AsyncClient with the Plane API's auth header."""

    def __init__(self, api_key: str, api_url: str, timeout: float = 30.0):
        self.api_url = api_url.rstrip("/")
        self._client = httpx.AsyncClient(
            headers={"x-api-key": api_key},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "PlaneClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()

    def _url(self, path: str) -> str:
        return f"{self.api_url}{path}"

    async def request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        resp = await self._client.request(
            method, self._url(path), json=json, params=params
        )
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return await self.request("POST", path, json=json)

    async def patch(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return await self.request("PATCH", path, json=json)

    async def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("DELETE", path, params=params)
