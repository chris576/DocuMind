import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from python_common.config_client import fetch_config_slice
from python_llm import LLMProviderFactory
from python_llm.config import LLMConfig, load_llm_config

from src.extraction_service import ExtractionService
from src.models import ExtractRequest, ExtractResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("extraction")

# Global service instance (built in the lifespan).
extraction_service: ExtractionService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global extraction_service

    logger.info("Starting Extraction Pipeline")

    llm_config = load_llm_config()

    # Admin-Panel config (gateway) overrides env; env remains fallback.
    llm_slice = await fetch_config_slice("llm")
    if llm_slice:
        llm_config = LLMConfig(**{**asdict(llm_config), **llm_slice})

    llm = LLMProviderFactory.create(llm_config.provider, llm_config.to_provider_config())

    db_url = os.getenv("PGVECTOR_URL")
    table = os.getenv("FACT_TABLE", "document_facts")
    batch_size = int(os.getenv("EXTRACTION_BATCH_SIZE", "10"))

    extraction_service = ExtractionService(llm, db_url, table_name=table, batch_size=batch_size)
    extraction_service.initialize()

    yield

    logger.info("Shutting down Extraction Pipeline")


app = FastAPI(title="Extraction Pipeline", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
async def status():
    if extraction_service is None:
        raise HTTPException(status_code=503, detail="Extraction service not initialized")
    return extraction_service.get_status()


@app.get("/health")
async def health():
    return {
        "status": "healthy" if extraction_service and extraction_service.ready else "unhealthy",
        "service": "extraction-pipeline",
    }


@app.post("/extract", response_model=ExtractResponse)
async def extract(request: ExtractRequest | None = None):
    if extraction_service is None or not extraction_service.ready:
        raise HTTPException(status_code=503, detail="Extraction service not initialized")
    try:
        result = await extraction_service.run(request.limit if request else None)
        return ExtractResponse(**result)
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
