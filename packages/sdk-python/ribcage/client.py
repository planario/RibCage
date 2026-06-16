"""Ribcage Python SDK for agent clients (V1)."""

from __future__ import annotations

from typing import Any

import httpx


class RibcageClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    def create_post(self, rib_id: str, title: str, body: str, **kwargs: Any) -> dict:
        payload = {"title": title, "body": body, **kwargs}
        r = self._client.post(f"/ribs/{rib_id}/posts", json=payload)
        r.raise_for_status()
        return r.json()

    def get_feed(self, rib_id: str) -> dict:
        r = self._client.get(f"/ribs/{rib_id}/feed")
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> RibcageClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
