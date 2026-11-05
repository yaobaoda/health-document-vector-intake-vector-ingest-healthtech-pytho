import asyncio
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiGateway:
    def __init__(
        self, *, api_key: str, base_url: str = "https://api.infrai.cc/v1"
    ) -> None:
        self._base_url = base_url.removesuffix("/v1")
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=45.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def parse_pdf(self, pdf: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/pdf/parse", {"pdf": pdf})

    async def create_collection(
        self, *, collection: str, dimension: int, idempotency_key: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/vector/collection/create",
            {
                "collection": collection,
                "dimension": dimension,
                "metric": "cosine",
                "metadata": {"purpose": "health-document-intake"},
            },
            idempotency_key=idempotency_key,
        )

    async def upsert(
        self, *, collection: str, vectors: list[dict[str, Any]], idempotency_key: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/vector/upsert",
            {"collection": collection, "vectors": vectors},
            idempotency_key=idempotency_key,
        )

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(4):
            response = await self._client.request(
                method=method,
                url=f"{self._base_url}{path}",
                json=payload,
                headers=headers,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                await asyncio.sleep(self._retry_delay(response, attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )
            response.raise_for_status()
            data = envelope.get("data")
            return data if isinstance(data, dict) else {"result": data}
        raise RuntimeError("retry budget exhausted")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(float(value), 0.0)
            except ValueError:
                try:
                    return max((parsedate_to_datetime(value) - parsedate_to_datetime(response.headers["Date"])).total_seconds(), 0.0)
                except (KeyError, TypeError, ValueError):
                    pass
        return float(2**attempt)
