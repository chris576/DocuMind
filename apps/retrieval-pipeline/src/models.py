from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SearchRequest(BaseModel):
    query: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    correspondent: Optional[str] = None
    max_results: int = 20

class SearchResult(BaseModel):
    title: str
    correspondent: str = ""
    date: str = ""
    score: float
    cross_score: float = 0.5
    snippet: str
    doc_id: Optional[int] = None
    content: str = ""

class ContextRequest(BaseModel):
    question: str
    max_sources: int = 5

class ContextResponse(BaseModel):
    context: str
    sources: List[dict]
    query: str

class IndexBuildRequest(BaseModel):
    """Documents pushed by the ingestion pipeline to rebuild the BM25 index."""
    documents: List[dict]

class SearchEngineStatus(BaseModel):
    initialized: bool = False
    chroma_ready: bool = False
    bm25_ready: bool = False
    documents_count: int = 0
    bm25_documents_count: int = 0
    last_updated: Optional[str] = None
