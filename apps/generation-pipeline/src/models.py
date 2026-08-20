from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

from python_llm import ChatMessage


class LLMProviderType(str, Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class ChatInitRequest(BaseModel):
    document_id: Optional[int] = None
    document_title: Optional[str] = None
    document_content: Optional[str] = None


class ChatMessageRequest(BaseModel):
    chat_id: str
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    chat_id: str
    message: str
    role: str = "assistant"


class GenerationStatus(BaseModel):
    initialized: bool = False
    provider: str = ""
    model: str = ""
    ready: bool = False
