import os
import logging
import json
from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, List, Dict

import openai
import anthropic

from .models import ChatMessage, GenerateRequest, GenerateResponse

logger = logging.getLogger("generation.providers")

class BaseLLMProvider(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "")
        self.provider_name = ""
    
    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        pass
    
    @abstractmethod
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        pass
    
    @abstractmethod
    async def chat(self, messages: List[ChatMessage], stream: bool = False) -> str:
        pass
    
    def _build_prompt(self, request: GenerateRequest) -> str:
        system_prompt = """You are a helpful assistant that answers questions based on the provided document context. 
        If the answer cannot be found in the context, say so clearly. Always cite which document you used."""
        
        context_section = ""
        if request.context:
            context_section = f"\n\nContext:\n{request.context}"
        
        if request.sources:
            sources_text = "\n\nSources:\n"
            for i, src in enumerate(request.sources, 1):
                sources_text += f"{i}. {src.get('title', 'Unknown')} ({src.get('correspondent', 'Unknown')}, {src.get('date', 'Unknown')})\n"
            context_section += sources_text
        
        return f"{system_prompt}{context_section}\n\nQuestion: {request.question}\n\nAnswer:"

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.provider_name = "openai"
        self.client = openai.AsyncOpenAI(
            api_key=config.get("api_key") or os.getenv("OPENAI_API_KEY")
        )
        self.model = config.get("model", "gpt-4")
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        prompt = self._build_prompt(request)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        return GenerateResponse(
            answer=response.choices[0].message.content,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            model=self.model,
            provider=self.provider_name
        )
    
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(request)
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def chat(self, messages: List[ChatMessage], stream: bool = False) -> str:
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages
        )
        
        return response.choices[0].message.content

class OllamaProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.provider_name = "ollama"
        self.base_url = config.get("base_url", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        self.model = config.get("model", "llama3.2")
        self.client = openai.AsyncOpenAI(
            base_url=f"{self.base_url}/v1",
            api_key="ollama"  # Ollama doesn't require a real API key
        )
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        prompt = self._build_prompt(request)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        return GenerateResponse(
            answer=response.choices[0].message.content,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
            model=self.model,
            provider=self.provider_name
        )
    
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(request)
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def chat(self, messages: List[ChatMessage], stream: bool = False) -> str:
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages
        )
        
        return response.choices[0].message.content

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.provider_name = "anthropic"
        self.client = anthropic.AsyncAnthropic(
            api_key=config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = config.get("model", "claude-3-sonnet-20240229")
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        prompt = self._build_prompt(request)
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return GenerateResponse(
            answer=response.content[0].text,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            model=self.model,
            provider=self.provider_name
        )
    
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(request)
        
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def chat(self, messages: List[ChatMessage], stream: bool = False) -> str:
        # Convert to Anthropic format
        formatted_messages = []
        for m in messages:
            if m.role in ["user", "assistant"]:
                formatted_messages.append({"role": m.role, "content": m.content})
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=formatted_messages
        )
        
        return response.content[0].text

class CustomProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.provider_name = "custom"
        self.base_url = config.get("base_url", os.getenv("CUSTOM_LLM_BASE_URL"))
        self.api_key = config.get("api_key", os.getenv("CUSTOM_LLM_API_KEY", ""))
        self.model = config.get("model", "default")
        
        self.client = openai.AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        prompt = self._build_prompt(request)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        return GenerateResponse(
            answer=response.choices[0].message.content,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
            model=self.model,
            provider=self.provider_name
        )
    
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(request)
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def chat(self, messages: List[ChatMessage], stream: bool = False) -> str:
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages
        )
        
        return response.choices[0].message.content

class LLMProviderFactory:
    @staticmethod
    def create(provider_type: str, config: dict) -> BaseLLMProvider:
        providers = {
            "openai": OpenAIProvider,
            "ollama": OllamaProvider,
            "anthropic": AnthropicProvider,
            "custom": CustomProvider,
        }
        
        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown LLM provider: {provider_type}")
        
        return provider_class(config)
