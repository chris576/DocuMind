from abc import ABC, abstractmethod
from typing import AsyncGenerator, List

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class GenerateRequest(BaseModel):
    question: str
    context: str = ""
    sources: List[dict] = Field(default_factory=list)
    max_tokens: int = 1000
    temperature: float = 0.7
    stream: bool = False


class GenerateResponse(BaseModel):
    answer: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""


class BaseLLMProvider(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "")
        self.provider_name = ""

    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        pass

    @abstractmethod
    async def generate_stream(
        self, request: GenerateRequest
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def chat(self, messages: List[ChatMessage], stream: bool = False) -> str:
        pass

    def _build_prompt(self, request: GenerateRequest) -> str:
        system_prompt = (
            "You are a helpful assistant that answers questions based on the provided document context. "
            "If the answer cannot be found in the context, say so clearly. Always cite which document you used."
        )

        context_section = ""
        if request.context:
            context_section = f"\n\nContext:\n{request.context}"

        if request.sources:
            sources_text = "\n\nSources:\n"
            for i, src in enumerate(request.sources, 1):
                sources_text += (
                    f"{i}. {src.get('title', 'Unknown')} "
                    f"({src.get('correspondent', 'Unknown')}, {src.get('date', 'Unknown')})\n"
                )
            context_section += sources_text

        return f"{system_prompt}{context_section}\n\nQuestion: {request.question}\n\nAnswer:"
