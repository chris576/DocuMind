from typing import List

from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    title: str
    correspondent: str = ""
    created: str = ""
    tags: List[str] = []
    hash: str = ""

class Document(BaseModel):
    id: int
    title: str
    content: str
    correspondent: str = ""
    created: str = ""
    tags: List[str] = []
    last_updated: str = ""
    hash: str = ""

class IngestionStatus(BaseModel):
    running: bool = False
    last_indexed: str | None = None
    documents_count: int = 0
    up_to_date: bool = False
    message: str = ""

class IngestionRequest(BaseModel):
    force: bool = False
    check_new: bool = False

class PaperlessConfig(BaseModel):
    api_url: str
    api_token: str
