"""Streaming HTTP client for Ollama's chat API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

import httpx

from zara_ai.config import AppConfig
from zara_ai.conversation.errors import (
    OllamaConnectionError,
    OllamaProtocolError,
    OllamaResponseError,
)


class OllamaClient:
    """Small async client that exposes Ollama chat as streamed text chunks."""

    def __init__(
        self,
        config: AppConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.ollama.base_url,
            timeout=httpx.Timeout(config.ollama.request_timeout_seconds),
            transport=transport,
        )

    async def stream_chat(
        self, messages: Sequence[Mapping[str, str]]
    ) -> AsyncIterator[str]:
        """Yield response text as it arrives; propagate cancellation promptly."""
        payload: dict[str, Any] = {
            "model": self._config.ollama.model,
            "messages": list(messages),
            "stream": True,
            "options": {
                "temperature": self._config.generation.temperature,
                "num_ctx": self._config.generation.num_ctx,
            },
        }
        try:
            async with self._client.stream(
                "POST", "/api/chat", json=payload
            ) as response:
                if response.is_error:
                    body = (await response.aread()).decode(
                        response.encoding or "utf-8", errors="replace"
                    )
                    raise OllamaResponseError(
                        f"Ollama returned HTTP {response.status_code}: "
                        f"{_short_message(body)}"
                    )

                completed = False
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise OllamaProtocolError(
                            "Ollama returned an invalid JSON stream line."
                        ) from error
                    if not isinstance(item, dict):
                        raise OllamaProtocolError(
                            "Ollama returned an unexpected stream value."
                        )
                    if item.get("error"):
                        raise OllamaResponseError(
                            f"Ollama error: {_short_message(str(item['error']))}"
                        )
                    message = item.get("message", {})
                    if not isinstance(message, dict):
                        raise OllamaProtocolError(
                            "Ollama returned an invalid message in its stream."
                        )
                    content = message.get("content", "")
                    if content and not isinstance(content, str):
                        raise OllamaProtocolError(
                            "Ollama returned non-text message content."
                        )
                    if content:
                        yield content
                    if item.get("done") is True:
                        completed = True
                        break

                if not completed:
                    raise OllamaProtocolError(
                        "Ollama ended the response before its completion signal."
                    )
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as error:
            raise OllamaConnectionError(
                "The request to Ollama timed out. Check the model and try again."
            ) from error
        except httpx.ConnectError as error:
            raise OllamaConnectionError(
                "Could not connect to Ollama. Check that Ollama is running."
            ) from error
        except httpx.HTTPError as error:
            raise OllamaConnectionError(
                f"The request to Ollama failed: {error}"
            ) from error

    async def list_models(self) -> list[str]:
        """Return model names reported by the local Ollama server."""
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise OllamaConnectionError(
                "The request to Ollama timed out while listing models."
            ) from error
        except httpx.ConnectError as error:
            raise OllamaConnectionError(
                "Could not connect to Ollama. Check that Ollama is running."
            ) from error
        except httpx.HTTPStatusError as error:
            raise OllamaResponseError(
                f"Ollama returned HTTP {error.response.status_code} "
                "while listing models."
            ) from error
        except httpx.HTTPError as error:
            raise OllamaConnectionError(
                f"Could not list Ollama models: {error}"
            ) from error

        try:
            payload = response.json()
            models = payload["models"]
            names = [model["name"] for model in models]
            if not all(isinstance(name, str) for name in names):
                raise TypeError("model names must be strings")
        except (ValueError, KeyError, TypeError) as error:
            raise OllamaProtocolError(
                "Ollama returned an invalid model list."
            ) from error
        return names

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.aclose()


def _short_message(message: str, limit: int = 300) -> str:
    compact = " ".join(message.split())
    return compact[:limit] if compact else "No error details provided."
