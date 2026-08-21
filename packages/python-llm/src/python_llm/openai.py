import logging
from collections.abc import AsyncGenerator
from typing import List

import openai

from .base import BaseLLMProvider, ChatMessage, GenerateRequest, GenerateResponse

logger = logging.getLogger("python_llm.openai")


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.provider_name = "openai"
        self.client = openai.AsyncOpenAI(
            api_key=config.get("api_key") or config.get("openai_api_key")
        )
        self.model = config.get("model", "gpt-4")

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        prompt = self._build_prompt(request)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        return GenerateResponse(
            answer=response.choices[0].message.content,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            model=self.model,
            provider=self.provider_name,
        )

    async def generate_stream(
        self, request: GenerateRequest
    ) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(request)

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat(self, messages: List[ChatMessage], stream: bool = False) -> str:
        formatted_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        response = await self.client.chat.completions.create(
            model=self.model, messages=formatted_messages
        )

        return response.choices[0].message.content
