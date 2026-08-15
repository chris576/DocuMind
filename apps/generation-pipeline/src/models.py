from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
from enum import Enum

class LLMProviderType(str, Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"

class GenerateRequest(BaseModel):
    question: str
    context: str = ""
    sources: List[dict] = []
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

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

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
