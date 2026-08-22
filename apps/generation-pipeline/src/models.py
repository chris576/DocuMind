from enum import Enum
from typing import List

from pydantic import BaseModel, Field
from python_llm import ChatMessage


class LLMProviderType(str, Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class ChatInitRequest(BaseModel):
    document_id: int | None = None
    document_title: str | None = None
    document_content: str | None = None


class ChatMessageRequest(BaseModel):
    chat_id: str
    message: str
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    chat_id: str
    message: str
    role: str = "assistant"


class GenerationStatus(BaseModel):
    initialized: bool = False
    provider: str = ""
    model: str = ""
    ready: bool = False
