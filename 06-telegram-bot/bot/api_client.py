"""Thin async client for the project-04 Conversion API."""

import httpx


class ApiError(Exception):
    pass


class ApiClient:
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 90.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key} if self.api_key else {}

    async def _post(self, path: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}{path}", headers=self._headers(), **kwargs
                )
            except httpx.HTTPError as e:
                raise ApiError(f"Conversion service unreachable: {e}") from e
        try:
            body = resp.json()
        except ValueError:
            raise ApiError(f"Conversion service returned {resp.status_code}")
        if resp.status_code != 200 or not body.get("ok"):
            raise ApiError(body.get("error") or body.get("detail") or f"HTTP {resp.status_code}")
        return body

    async def convert_file(self, filename: str, data: bytes) -> dict:
        return await self._post("/api/convert/file", files={"file": (filename, data)})

    async def convert_url(self, url: str) -> dict:
        return await self._post("/api/convert/url", json={"url": url})

    async def convert_youtube(self, url: str) -> dict:
        return await self._post("/api/convert/youtube", json={"url": url})

    async def formats(self) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.base_url}/api/formats", headers=self._headers())
        return resp.json()
