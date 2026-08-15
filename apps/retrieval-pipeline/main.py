import os
import logging
import requests
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.search_engine import SearchEngine
from src.models import SearchRequest, SearchResult, ContextRequest, ContextResponse
from src.messaging import RabbitMQClient
from src.message_handlers import MessageHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("retrieval")

# Global instance
search_engine: SearchEngine = None
rabbitmq_client: RabbitMQClient = None
message_handler: MessageHandler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global search_engine, rabbitmq_client, message_handler

    logger.info("Starting Retrieval Pipeline")

    config = {
        "chroma_url": os.getenv("CHROMA_URL", "http://localhost:8000"),
        "collection_name": os.getenv("COLLECTION_NAME", "documents"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"),
        "cross_encoder_model": os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        "bm25_weight": float(os.getenv("BM25_WEIGHT", "0.3")),
        "semantic_weight": float(os.getenv("SEMANTIC_WEIGHT", "0.7")),
        "max_results": int(os.getenv("MAX_RESULTS", "20")),
        "bm25_file": os.getenv("BM25_FILE", "./data/bm25_index.pkl"),
    }

    search_engine = SearchEngine(config)
    search_engine.initialize()
    search_engine.setup_chroma()

    # Try to load BM25 index or build from documents
    if not search_engine._load_bm25():
        logger.info("No BM25 index found, will build when documents are available")

    # Connect to RabbitMQ
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    rabbitmq_client = RabbitMQClient(rabbitmq_url)
    connected = await rabbitmq_client.connect("retrieval")

    if connected:
        message_handler = MessageHandler(rabbitmq_client, search_engine)
        await rabbitmq_client.consume(message_handler.handle_retrieval_message)
        logger.info("RabbitMQ consumer started")
    else:
        logger.warning("RabbitMQ not available, continuing without messaging")

    yield

    if rabbitmq_client:
        await rabbitmq_client.close()

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
async def build_index():
    """Trigger BM25 index rebuild - should be called after ingestion"""
    try:
        # In a real implementation, this would fetch documents from a shared cache
        # or receive them via message queue from the ingestion pipeline
        return {"status": "not_implemented", "message": "Index building from external source not yet implemented"}
    except Exception as e:
        logger.error(f"Index build error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
