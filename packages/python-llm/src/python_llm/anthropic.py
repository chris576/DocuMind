import logging
from collections.abc import AsyncGenerator
from typing import List

import anthropic

from .base import BaseLLMProvider, ChatMessage, GenerateRequest, GenerateResponse

logger = logging.getLogger("python_llm.anthropic")


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.provider_name = "anthropic"
        self.client = anthropic.AsyncAnthropic(
            api_key=config.get("api_key") or config.get("anthropic_api_key")
        )
        self.model = config.get("model", "claude-3-sonnet-20240229")

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        prompt = self._build_prompt(request)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        return GenerateResponse(
            answer=response.content[0].text,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            model=self.model,
            provider=self.provider_name,
        )

    async def generate_stream(
        self, request: GenerateRequest
    ) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(request)

        async with self.client.messages.stream(
            model=self.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def chat(self, messages: List[ChatMessage], stream: bool = False) -> str:
        formatted_messages = []
        for m in messages:
            if m.role in ["user", "assistant"]:
                formatted_messages.append({"role": m.role, "content": m.content})

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=formatted_messages,
        )

        return response.content[0].text
