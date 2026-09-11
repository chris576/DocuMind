import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from python_common.config_client import fetch_config_slice
from python_dms import DocumentProviderFactory
from python_dms.config import DMSConfig, load_dms_config
from python_vectordb.config import VectorDBConfig, load_vector_db_config
from python_vectordb.vector_db import VectorDBFactory

from src.ingestion_service import IngestionService
from src.models import IngestionRequest
from src.tasks import IngestionTask

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingestion")

# Global instances
ingestion_service: IngestionService | None = None
ingestion_task: IngestionTask | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ingestion_service, ingestion_task

    logger.info("Starting Ingestion Pipeline")

    dms_config = load_dms_config()
    vector_db_config = load_vector_db_config()

    # Admin-Panel config (gateway) overrides env; env remains fallback.
    dms_slice = await fetch_config_slice("dms")
    if dms_slice:
        dms_config = DMSConfig(**{**asdict(dms_config), **dms_slice})
    vector_slice = await fetch_config_slice("vector-db")
    if vector_slice:
        vector_db_config = VectorDBConfig(**{**asdict(vector_db_config), **vector_slice})

    # Write-only vector database access (CQRS): ingestion never reads.
    vector_db = VectorDBFactory.create_writer(vector_db_config.to_vector_db_config())
    document_provider = DocumentProviderFactory.create(dms_config.to_document_provider_config())

    ingestion_service = IngestionService(document_provider, vector_db)
    ingestion_task = IngestionTask(ingestion_service)

    yield

    logger.info("Shutting down Ingestion Pipeline")


app = FastAPI(title="Ingestion Pipeline", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
async def status():
    if ingestion_service is None:
        raise HTTPException(status_code=503, detail="Ingestion service not initialized")
    return ingestion_service.get_status()


@app.get("/health")
async def health():
    return {
        "status": "healthy" if ingestion_service and ingestion_service.is_initialized else "unhealthy",
        "service": "ingestion-pipeline",
    }


async def _push_documents_to_retrieval():
    """Compatibility notification to the retrieval pipeline (deprecated).

    The keyword index is now maintained on the ingestion write path (the same
    IndexDocumentsCommand feeds the adapter's keyword channel). This routine
    only logs; it no longer triggers a BM25 rebuild on the read side.
    """
    if ingestion_service is None:
        return
    documents = [asdict(doc) for doc in ingestion_service.documents]

    if not documents:
        logger.info("No documents to push to retrieval pipeline")
        return

    logger.info(
        f"{len(documents)} documents indexed via write path "
        "(keyword index maintained by adapter; retrieval push deprecated)"
    )


async def _run_ingestion_and_push(force_update: bool, check_new: bool):
    """Run ingestion and, on success, notify the retrieval pipeline."""
    if ingestion_task is None:
        logger.error("Ingestion task not initialized; cannot run")
        return
    try:
        result = ingestion_task.run(force_update=force_update, check_new=check_new)
        if result.get("status") == "completed":
            await _push_documents_to_retrieval()
    except Exception as e:
        logger.error(f"Ingestion background run failed: {str(e)}")


@app.post("/ingest")
async def ingest(request: IngestionRequest, background_tasks: BackgroundTasks):
    if ingestion_task is None:
        raise HTTPException(status_code=503, detail="Ingestion task not initialized")
    if ingestion_task.running:
        return {"status": "running", "message": "Ingestion already in progress"}

    background_tasks.add_task(_run_ingestion_and_push, request.force, request.check_new)

    return {"status": "started", "message": "Ingestion started in background"}


@app.post("/ingest/sync")
async def ingest_sync(request: IngestionRequest):
    if ingestion_task is None:
        raise HTTPException(status_code=503, detail="Ingestion task not initialized")
    if ingestion_task.running:
        return {"status": "running", "message": "Ingestion already in progress"}

    result = ingestion_task.run(force_update=request.force, check_new=request.check_new)
    if result.get("status") == "completed":
        await _push_documents_to_retrieval()
    return result


@app.post("/check")
async def check_updates():
    if ingestion_service is None:
        raise HTTPException(status_code=503, detail="Ingestion service not initialized")
    needs_update, message = ingestion_service.check_for_updates()
    return {"needs_update": needs_update, "message": message}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
