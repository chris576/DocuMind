import os
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from python_common.env import get_env
from python_common.http import post_json
from python_dms.config import load_dms_config
from python_dms import DocumentProviderFactory
from python_vectordb.config import load_vector_db_config
from python_vectordb.vector_db import VectorDBFactory

from src.ingestion_service import IngestionService
from src.tasks import IngestionTask
from src.models import IngestionRequest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ingestion")

# Global instances
ingestion_service: IngestionService = None
ingestion_task: IngestionTask = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ingestion_service, ingestion_task

    logger.info("Starting Ingestion Pipeline")

    dms_config = load_dms_config()
    vector_db_config = load_vector_db_config()

    # Write-only vector database access (CQRS): ingestion never reads.
    vector_db = VectorDBFactory.create_writer(vector_db_config.to_vector_db_config())
    document_provider = DocumentProviderFactory.create(
        dms_config.to_document_provider_config()
    )

    ingestion_service = IngestionService(document_provider, vector_db)
    ingestion_task = IngestionTask(ingestion_service)

    yield

    logger.info("Shutting down Ingestion Pipeline")

app = FastAPI(
    title="Ingestion Pipeline",
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
    return ingestion_service.get_status()

@app.get("/health")
async def health():
    return {
        "status": "healthy" if ingestion_service.is_initialized else "unhealthy",
        "service": "ingestion-pipeline"
    }

async def _push_documents_to_retrieval():
    """Push all loaded documents to the retrieval pipeline to rebuild its BM25 index."""
    retrieval_url = get_env("RETRIEVAL_PIPELINE_URL", "http://localhost:8002")
    documents = [asdict(doc) for doc in ingestion_service.documents]

    if not documents:
        logger.info("No documents to push to retrieval pipeline")
        return

    logger.info(f"Pushing {len(documents)} documents to retrieval pipeline")
    await post_json(f"{retrieval_url}/index/build", {"documents": documents})


async def _run_ingestion_and_push(force_update: bool, check_new: bool):
    """Run ingestion and, on success, notify the retrieval pipeline."""
    try:
        result = ingestion_task.run(force_update=force_update, check_new=check_new)
        if result.get("status") == "completed":
            await _push_documents_to_retrieval()
    except Exception as e:
        logger.error(f"Ingestion background run failed: {str(e)}")


@app.post("/ingest")
async def ingest(request: IngestionRequest, background_tasks: BackgroundTasks):
    if ingestion_task.running:
        return {"status": "running", "message": "Ingestion already in progress"}

    background_tasks.add_task(_run_ingestion_and_push, request.force, request.check_new)

    return {"status": "started", "message": "Ingestion started in background"}

@app.post("/ingest/sync")
async def ingest_sync(request: IngestionRequest):
    if ingestion_task.running:
        return {"status": "running", "message": "Ingestion already in progress"}

    result = ingestion_task.run(force_update=request.force, check_new=request.check_new)
    if result.get("status") == "completed":
        await _push_documents_to_retrieval()
    return result

@app.post("/check")
async def check_updates():
    needs_update, message = ingestion_service.check_for_updates()
    return {"needs_update": needs_update, "message": message}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
