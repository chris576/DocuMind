import logging
from collections.abc import AsyncGenerator
from typing import List

import httpx

from .base import BaseLLMProvider, ChatMessage, GenerateRequest, GenerateResponse

logger = logging.getLogger("python_llm.opencode")

DEFAULT_BASE_URL = "http://127.0.0.1:4096"
DEFAULT_USERNAME = "opencode"


class OpenCodeProvider(BaseLLMProvider):
    """LLM provider that talks to a headless ``opencode serve`` instance.

    OpenCode exposes its own OpenAPI 3.1 HTTP API (not an OpenAI-compatible
    one). This provider creates a session and sends a single text prompt via
    ``POST /session/{id}/message``, then joins the returned text parts.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.provider_name = "opencode"

        self.base_url = (
            config.get("opencode_base_url") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.username = config.get("opencode_username") or DEFAULT_USERNAME
        self.password = config.get("opencode_password") or ""

        # OpenCode model IDs are "providerID/modelID"; omit the model in the
        # request when unset so OpenCode falls back to its configured default.
        self.model = config.get("opencode_model") or ""

        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        self._auth = (
            httpx.BasicAuth(self.username, self.password)
            if self.password
            else None
        )

    def _model_body(self) -> dict:
        """Build the optional ``model`` field from ``providerID/modelID``."""
        if not self.model:
            return {}
        provider_id, _, model_id = self.model.partition("/")
        body: dict = {}
        if provider_id:
            body["providerID"] = provider_id
        if model_id:
            body["modelID"] = model_id
        return {"model": body} if body else {}

    async def _create_session(self) -> str:
        response = await self._client.post(
            "/session",
            json={"title": "python-llm"},
            auth=self._auth,
        )
        response.raise_for_status()
        return response.json()["id"]

    async def _prompt(self, session_id: str, text: str) -> str:
        body = {
            **self._model_body(),
            "parts": [{"type": "text", "text": text}],
        }
        response = await self._client.post(
            f"/session/{session_id}/message",
            json=body,
            auth=self._auth,
        )
        response.raise_for_status()
        return self._extract_text(response.json())

    @staticmethod
    def _extract_text(payload: dict) -> str:
        parts = payload.get("parts") or []
        chunks = [
            part["text"]
            for part in parts
            if part.get("type") == "text" and part.get("text")
        ]
        return "\n".join(chunks)

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        prompt = self._build_prompt(request)

        session_id = await self._create_session()
        answer = await self._prompt(session_id, prompt)

        return GenerateResponse(
            answer=answer,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            model=self.model,
            provider=self.provider_name,
        )

    async def generate_stream(
        self, request: GenerateRequest
    ) -> AsyncGenerator[str, None]:
        # OpenCode has no OpenAI-style token stream; the whole answer is
        # delivered as a single chunk once the session message completes.
        response = await self.generate(request)
        yield response.answer

    async def chat(self, messages: List[ChatMessage], stream: bool = False) -> str:
        text = "\n".join(f"{m.role}: {m.content}" for m in messages)

        session_id = await self._create_session()
        return await self._prompt(session_id, text)
