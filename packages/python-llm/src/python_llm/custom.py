import logging
from collections.abc import AsyncGenerator
from typing import List

import openai

from .base import BaseLLMProvider, ChatMessage, GenerateRequest, GenerateResponse

logger = logging.getLogger("python_llm.custom")


class CustomProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.provider_name = "custom"
        self.base_url = config.get("base_url") or config.get("custom_base_url")
        self.api_key = config.get("api_key") or config.get("custom_api_key", "")
        self.model = config.get("model", config.get("custom_model", "default"))

        self.client = openai.AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

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
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens
            if response.usage
            else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
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
