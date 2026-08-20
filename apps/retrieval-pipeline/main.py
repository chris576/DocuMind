import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from python_vectordb.config import load_vector_db_config

from src.search_engine import SearchEngine
from src.models import SearchRequest, SearchResult, ContextRequest, ContextResponse, IndexBuildRequest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("retrieval")

# Global instance
search_engine: SearchEngine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global search_engine

    logger.info("Starting Retrieval Pipeline")

    vector_db_config = load_vector_db_config()
    config = {
        "vector_db_type": vector_db_config.vector_db_type,
        "chroma_url": vector_db_config.chroma_url,
        "qdrant_url": vector_db_config.qdrant_url,
        "qdrant_api_key": vector_db_config.qdrant_api_key,
        "pgvector_url": vector_db_config.pgvector_url,
        "collection_name": vector_db_config.collection_name,
        "embedding_model": vector_db_config.embedding_model,
        "embedding_provider": vector_db_config.embedding_provider,
        "cross_encoder_model": vector_db_config.cross_encoder_model,
        "bm25_weight": float(os.getenv("BM25_WEIGHT", "0.3")),
        "semantic_weight": float(os.getenv("SEMANTIC_WEIGHT", "0.7")),
        "max_results": int(os.getenv("MAX_RESULTS", "20")),
        "bm25_file": os.getenv("BM25_FILE", "./data/bm25_index.pkl"),
    }

    search_engine = SearchEngine(config)
    search_engine.initialize()
    search_engine.setup_vector_db()

    # Try to load BM25 index or build from documents
    if not search_engine._load_bm25():
        logger.info("No BM25 index found, will build when documents are available")

    yield

    logger.info("Shutting down Retrieval Pipeline")

app = FastAPI(
    title="Retrieval Pipeline",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
async def status():
    return search_engine.get_status()

@app.get("/health")
async def health():
    return {
        "status": "healthy" if search_engine.is_initialized else "unhealthy",
        "service": "retrieval-pipeline"
    }

@app.post("/search", response_model=list[SearchResult])
async def search(request: SearchRequest):
    try:
        if not search_engine.is_initialized:
            raise HTTPException(status_code=503, detail="Search engine not initialized")

        results = search_engine.search(request)
        return results
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/context", response_model=ContextResponse)
async def get_context(request: ContextRequest):
    try:
        if not search_engine.is_initialized:
            raise HTTPException(status_code=503, detail="Search engine not initialized")

        search_request = SearchRequest(query=request.question, max_results=request.max_sources)
        results = search_engine.search(search_request)

        context = ""
        sources = []

        for i, result in enumerate(results[:request.max_sources]):
            context += f"Document {i+1}: {result.title}\n{result.snippet}\n\n"
            sources.append({
                "title": result.title,
                "correspondent": result.correspondent,
                "date": result.date,
                "snippet": result.snippet,
                "doc_id": result.doc_id
            })

        return ContextResponse(
            context=context if context else "No relevant documents found.",
            sources=sources,
            query=request.question
        )
    except Exception as e:
        logger.error(f"Context error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/index/build")
async def build_index(request: IndexBuildRequest):
    """Rebuild the BM25 index from documents pushed by the ingestion pipeline."""
    try:
        if not request.documents:
            return {"status": "completed", "documents_count": 0, "message": "No documents provided"}

        success = search_engine.setup_bm25(request.documents)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to build BM25 index")

        return {
            "status": "completed",
            "documents_count": len(request.documents),
            "bm25_documents_count": search_engine.status.bm25_documents_count,
        }
    except Exception as e:
        logger.error(f"Index build error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
