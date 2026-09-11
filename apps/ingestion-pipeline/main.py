import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from python_common.config_client import fetch_config_slice
from python_dms import DocumentProviderFactory
from python_dms.config import load_dms_config
from python_vectordb.config import VectorDBConfig, load_vector_db_config
from python_vectordb.vector_db import VectorDBFactory

from src.coordinator import IngestionCoordinator, IngestionTarget
from src.ingestion_service import IngestionService
from src.models import IngestionRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingestion")

# Global coordinator (multi-target). Built in the lifespan.
coordinator: IngestionCoordinator | None = None


def _env_fallback_connectors(vector_db_config: VectorDBConfig) -> list[dict]:
    """Single Paperless connector derived from env when the gateway is absent."""
    dms_config = load_dms_config()
    return [
        {
            "id": "paperless",
            "type": dms_config.document_provider,
            "url": dms_config.document_provider_url,
            "token": dms_config.document_provider_token,
            "collection": vector_db_config.collection_name,
        }
    ]


def _build_coordinator(connectors: list[dict], vector_db_config: VectorDBConfig) -> IngestionCoordinator:
    collections = [c.get("collection") or c.get("id") or "documents" for c in connectors]
    writers = VectorDBFactory.create_writers(
        vector_db_config.to_vector_db_config(), collections
    )

    targets = []
    for connector in connectors:
        collection = connector.get("collection") or connector.get("id") or "documents"
        provider = DocumentProviderFactory.create(
            {
                "type": connector.get("type", "paperless"),
                "url": connector.get("url"),
                "token": connector.get("token"),
            }
        )
        targets.append(
            IngestionTarget(
                id=connector.get("id", collection),
                collection=collection,
                service=IngestionService(provider, writers[collection]),
            )
        )

    return IngestionCoordinator(targets)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global coordinator

    logger.info("Starting Ingestion Pipeline")

    vector_db_config = load_vector_db_config()

    # Admin-Panel config (gateway) overrides env; env remains fallback.
    vector_slice = await fetch_config_slice("vector-db")
    if vector_slice:
        vector_db_config = VectorDBConfig(**{**asdict(vector_db_config), **vector_slice})
    connectors = await fetch_config_slice("connectors")
    if not connectors:
        connectors = _env_fallback_connectors(vector_db_config)

    coordinator = _build_coordinator(list(connectors), vector_db_config)

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
    if coordinator is None:
        raise HTTPException(status_code=503, detail="Ingestion service not initialized")
    return coordinator.get_status()


@app.get("/health")
async def health():
    healthy = bool(coordinator) and bool(coordinator.targets) and all(
        target.service.is_initialized for target in coordinator.targets
    )
    return {
        "status": "healthy" if healthy else "unhealthy",
        "service": "ingestion-pipeline",
    }


async def _push_documents_to_retrieval():
    """Compatibility notification to the retrieval pipeline (deprecated)."""
    if coordinator is None:
        return
    documents = [
        asdict(doc)
        for target in coordinator.targets
        for doc in target.service.documents
    ]

    if not documents:
        logger.info("No documents to push to retrieval pipeline")
        return

    logger.info(
        f"{len(documents)} documents indexed via write path "
        "(keyword index maintained by adapter; retrieval push deprecated)"
    )


async def _run_ingestion_and_push(force_update: bool, check_new: bool):
    """Run ingestion across all targets and, on success, notify retrieval."""
    if coordinator is None:
        logger.error("Ingestion coordinator not initialized; cannot run")
        return
    try:
        result = coordinator.run(force_update=force_update, check_new=check_new)
        if result.get("status") == "completed":
            await _push_documents_to_retrieval()
    except Exception as e:
        logger.error(f"Ingestion background run failed: {str(e)}")


@app.post("/ingest")
async def ingest(request: IngestionRequest, background_tasks: BackgroundTasks):
    if coordinator is None:
        raise HTTPException(status_code=503, detail="Ingestion service not initialized")
    if coordinator.running:
        return {"status": "running", "message": "Ingestion already in progress"}

    background_tasks.add_task(_run_ingestion_and_push, request.force, request.check_new)

    return {"status": "started", "message": "Ingestion started in background"}


@app.post("/ingest/sync")
async def ingest_sync(request: IngestionRequest):
    if coordinator is None:
        raise HTTPException(status_code=503, detail="Ingestion service not initialized")
    if coordinator.running:
        return {"status": "running", "message": "Ingestion already in progress"}

    result = coordinator.run(force_update=request.force, check_new=request.check_new)
    if result.get("status") == "completed":
        await _push_documents_to_retrieval()
    return result


@app.post("/check")
async def check_updates():
    if coordinator is None:
        raise HTTPException(status_code=503, detail="Ingestion service not initialized")
    needs_update, message = coordinator.check_for_updates()
    return {"needs_update": needs_update, "message": message}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
