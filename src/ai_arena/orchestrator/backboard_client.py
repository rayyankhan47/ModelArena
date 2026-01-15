"""Backboard API client wrapper."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


@dataclass
class BackboardConfig:
    """Configuration for Backboard API client."""

    api_key: str
    base_url: str = "https://app.backboard.io/api"
    timeout: int = 30
    max_retries: int = 2
    retry_backoff_sec: float = 1.0


class BackboardClient:
    """Thin Backboard API wrapper for assistants, threads, messages, tools, and documents."""

    def __init__(self, config: BackboardConfig):
        self.config = config
        self.headers = {"X-API-Key": self.config.api_key}

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        form_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retries."""
        url = f"{self.config.base_url}{path}"
        last_exc: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_body,
                    data=form_data,
                    files=files,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                if response.content:
                    return response.json()
                return {}
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_backoff_sec * (attempt + 1))
                    continue
                raise

        raise last_exc  # pragma: no cover

    # Assistants
    def create_assistant(
        self,
        name: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        embedding_provider: Optional[str] = None,
        embedding_model_name: Optional[str] = None,
        embedding_dims: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"name": name}
        if system_prompt is not None:
            payload["system_prompt"] = system_prompt
        if tools is not None:
            payload["tools"] = tools
        if embedding_provider is not None:
            payload["embedding_provider"] = embedding_provider
        if embedding_model_name is not None:
            payload["embedding_model_name"] = embedding_model_name
        if embedding_dims is not None:
            payload["embedding_dims"] = embedding_dims
        return self._request("POST", "/assistants", json_body=payload)

    def get_assistant(self, assistant_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/assistants/{assistant_id}")

    def update_assistant(
        self,
        assistant_id: str,
        name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if system_prompt is not None:
            payload["system_prompt"] = system_prompt
        if tools is not None:
            payload["tools"] = tools
        return self._request("PUT", f"/assistants/{assistant_id}", json_body=payload)

    def delete_assistant(self, assistant_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/assistants/{assistant_id}")

    def list_assistants(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        return self._request("GET", "/assistants", params={"skip": skip, "limit": limit})

    # Threads
    def create_thread(self, assistant_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/assistants/{assistant_id}/threads", json_body={})

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/threads/{thread_id}")

    def list_threads(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        return self._request("GET", "/threads", params={"skip": skip, "limit": limit})

    def delete_thread(self, thread_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/threads/{thread_id}")

    # Messages
    def post_message(
        self,
        thread_id: str,
        content: Optional[str] = None,
        *,
        llm_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        memory: str = "off",
        web_search: str = "off",
        send_to_llm: bool = True,
        stream: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        files: Optional[List[tuple]] = None,
    ) -> Dict[str, Any]:
        """Post a message to a thread.

        Args:
            files: list of tuples compatible with requests, e.g. [("files", ("rules.md", b"...", "text/markdown"))]
        """
        form_data: Dict[str, Any] = {
            "content": content or "",
            "llm_provider": llm_provider or "",
            "model_name": model_name or "",
            "memory": memory,
            "web_search": web_search,
            "send_to_llm": "true" if send_to_llm else "false",
            "stream": "true" if stream else "false",
            "metadata": json.dumps(metadata) if metadata else "",
        }

        files_payload = files if files else None
        return self._request(
            "POST",
            f"/threads/{thread_id}/messages",
            form_data=form_data,
            files=files_payload,
        )

    def submit_tool_outputs(
        self,
        thread_id: str,
        run_id: str,
        tool_outputs: List[Dict[str, str]],
        stream: bool = False,
    ) -> Dict[str, Any]:
        payload = {"tool_outputs": tool_outputs}

        # Backboard endpoint naming has varied; try a few known variants.
        candidate_paths = [
            f"/threads/{thread_id}/runs/{run_id}/submit-tool-outputs",
            f"/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
            f"/threads/{thread_id}/runs/{run_id}/submit-tool-outputs/",
            f"/threads/{thread_id}/runs/{run_id}/submit_tool_outputs/",
            f"/runs/{run_id}/submit-tool-outputs",
            f"/runs/{run_id}/submit_tool_outputs",
        ]

        last_exc: Optional[Exception] = None
        for path in candidate_paths:
            try:
                return self._request(
                    "POST",
                    path,
                    params={"stream": "true" if stream else "false"},
                    json_body=payload,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                resp = getattr(exc, "response", None)
                status = getattr(resp, "status_code", None)
                # Only fall back on "Not Found" style errors.
                if status == 404:
                    continue
                raise

        raise last_exc  # pragma: no cover

    # Documents
    def upload_document_to_thread(self, thread_id: str, file_tuple: tuple) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/threads/{thread_id}/documents",
            files={"file": file_tuple},
        )

    def upload_document_to_assistant(self, assistant_id: str, file_tuple: tuple) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/assistants/{assistant_id}/documents",
            files={"file": file_tuple},
        )

    def get_document_status(self, document_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/documents/{document_id}/status")

    def delete_document(self, document_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/documents/{document_id}")

    # Models
    def list_models(
        self,
        model_type: Optional[str] = None,
        provider: Optional[str] = None,
        supports_tools: Optional[bool] = None,
        min_context: Optional[int] = None,
        max_context: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"skip": skip, "limit": limit}
        if model_type:
            params["model_type"] = model_type
        if provider:
            params["provider"] = provider
        if supports_tools is not None:
            params["supports_tools"] = "true" if supports_tools else "false"
        if min_context is not None:
            params["min_context"] = min_context
        if max_context is not None:
            params["max_context"] = max_context
        return self._request("GET", "/models", params=params)

    def list_model_providers(self) -> Dict[str, Any]:
        return self._request("GET", "/models/providers")

