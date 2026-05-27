import re
from datetime import datetime
from html import unescape
from typing import Any

import httpx
from bs4 import BeautifulSoup


class ConfluenceClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token

    def _headers(self) -> dict[str, str]:
        import base64
        token = base64.b64encode(f"user:{self.api_token}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
        }

    async def list_pages_in_spaces(
        self, space_keys: list[str], since: datetime | None = None
    ) -> list[dict[str, Any]]:
        pages = []
        cql_parts = [f'space in ({",".join(space_keys)})', "type=page"]
        if since:
            cql_parts.append(f'lastmodified >= "{since.strftime("%Y-%m-%d")}"')
        cql = " AND ".join(cql_parts)

        async with httpx.AsyncClient(timeout=60.0) as client:
            start = 0
            while True:
                response = await client.get(
                    f"{self.base_url}/rest/api/content/search",
                    headers=self._headers(),
                    params={"cql": cql, "limit": 50, "start": start, "expand": "body.storage,version"},
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                if not results:
                    break
                pages.extend(results)
                if data.get("_links", {}).get("next"):
                    start += len(results)
                else:
                    break
        return pages

    def page_to_text(self, page: dict[str, Any]) -> str:
        storage = page.get("body", {}).get("storage", {}).get("value", "")
        if not storage:
            return page.get("title", "")
        soup = BeautifulSoup(storage, "lxml")
        text = soup.get_text(separator="\n", strip=True)
        return unescape(text)

    def page_metadata(self, page: dict[str, Any], base_url: str) -> dict[str, Any]:
        version = page.get("version", {})
        links = page.get("_links", {})
        webui = links.get("webui", "")
        return {
            "page_id": page["id"],
            "title": page.get("title", ""),
            "url": f"{base_url}{webui}" if webui else base_url,
            "version": version.get("number", 1),
            "last_modified": version.get("when"),
        }


def strip_confluence_macros(html: str) -> str:
    return re.sub(r"<ac:[^>]+>.*?</ac:[^>]+>", "", html, flags=re.DOTALL)
