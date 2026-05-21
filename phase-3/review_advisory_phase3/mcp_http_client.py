"""HTTP client for the hosted Google MCP server (OpenAPI, no direct Google APIs)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MCPHttpConfig:
    base_url: str
    timeout_s: float = 90.0


class MCPHttpError(RuntimeError):
    pass


def interpret_mcp_response(response: dict[str, Any], *, operation: str) -> None:
    """Raise MCPHttpError when the MCP server returns HTTP 200 with status=error."""
    status = str(response.get("status", "")).lower()
    if status == "success":
        return
    if status == "error":
        parts = [response.get("message"), response.get("details")]
        message = " — ".join(str(p) for p in parts if p) or str(response)
        raise MCPHttpError(f"MCP {operation} failed: {message}")
    if status:
        raise MCPHttpError(f"MCP {operation} returned unexpected status {status!r}: {response}")


class GoogleMCPHttpClient:
    """Calls the MCP server's REST tools: append_to_doc, create_email_draft."""

    def __init__(self, config: MCPHttpConfig) -> None:
        self._config = config

    def append_to_doc(self, *, doc_id: str, content: str) -> dict[str, Any]:
        return self._post_json(
            "/append_to_doc",
            {"doc_id": doc_id, "content": content},
        )

    def create_email_draft(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
        return self._post_json(
            "/create_email_draft",
            {"to": to, "subject": subject, "body": body},
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        base = self._config.base_url.rstrip("/")
        url = f"{base}{path}"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "ReviewAdvisoryAgent-Phase3/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._config.timeout_s) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise MCPHttpError(f"MCP HTTP {exc.code} on {path}: {body}") from exc
        except urllib.error.URLError as exc:
            raise MCPHttpError(f"MCP request failed for {path}: {exc}") from exc

        if not raw.strip():
            return {}
        try:
            parsed: Any = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MCPHttpError(f"MCP returned non-JSON from {path}: {raw[:500]}") from exc
        if not isinstance(parsed, dict):
            raise MCPHttpError(f"MCP response for {path} must be a JSON object.")
        return parsed
