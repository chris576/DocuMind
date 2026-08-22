import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from python_vectordb.config import load_vector_db_config

from src.models import (
    ContextRequest,
    ContextResponse,
    IndexBuildRequest,
    SearchRequest,
    SearchResult,
)
from src.search_engine import SearchEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("retrieval")

# Global instance
search_engine: SearchEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global search_engine

    logger.info("Starting Retrieval Pipeline")

    vector_db_config = load_vector_db_config()
    # Reuse the shared config projection (includes keyword method/weights +
    # FTS language). Only pipeline-specific knobs stay env-driven.
    config = vector_db_config.to_vector_db_config()
    config.update(
        {
            "max_results": int(os.getenv("MAX_RESULTS", "20")),
        }
    )

    search_engine = SearchEngine(config)
    search_engine.initialize()
    search_engine.setup_vector_db()

    yield

    logger.info("Shutting down Retrieval Pipeline")


app = FastAPI(title="Retrieval Pipeline", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
async def status():
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine not initialized")
    return search_engine.get_status()


@app.get("/health")
async def health():
    return {
        "status": "healthy" if search_engine and search_engine.is_initialized else "unhealthy",
        "service": "retrieval-pipeline",
    }


@app.post("/search", response_model=list[SearchResult])
async def search(request: SearchRequest):
    if search_engine is None or not search_engine.is_initialized:
        raise HTTPException(status_code=503, detail="Search engine not initialized")
    try:
        results = search_engine.search(request)
        return results
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/context", response_model=ContextResponse)
async def get_context(request: ContextRequest):
    if search_engine is None or not search_engine.is_initialized:
        raise HTTPException(status_code=503, detail="Search engine not initialized")
    try:
        search_request = SearchRequest(query=request.question, max_results=request.max_sources)
        results = search_engine.search(search_request)

        context = ""
        sources = []

        for i, result in enumerate(results[: request.max_sources]):
            context += f"Document {i + 1}: {result.title}\n{result.snippet}\n\n"
            sources.append(
                {
                    "title": result.title,
                    "correspondent": result.correspondent,
                    "date": result.date,
                    "snippet": result.snippet,
                    "doc_id": result.doc_id,
                }
            )

        return ContextResponse(
            context=context if context else "No relevant documents found.", sources=sources, query=request.question
        )
    except Exception as e:
        logger.error(f"Context error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/index/build")
async def build_index(request: IndexBuildRequest):
    """Compatibility endpoint (deprecated).

    Keyword indexing now happens on the ingestion write path: the same
    ``IndexDocumentsCommand`` that upserts vectors also feeds the adapter's
    keyword channel (native BM25 / FTS / local BM25). This read-side endpoint
    no longer builds an index itself.
    """
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine not initialized")
    return {
        "status": "completed",
        "documents_count": len(request.documents),
        "message": "Keyword index is maintained via ingestion (write path)",
        "deprecated": True,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
