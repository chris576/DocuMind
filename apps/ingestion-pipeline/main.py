import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from src.data_manager import DataManager
from src.tasks import IngestionTask
from src.models import IngestionRequest
from src.messaging import RabbitMQClient
from src.message_handlers import MessageHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ingestion")

# Global instances
data_manager: DataManager = None
ingestion_task: IngestionTask = None
rabbitmq_client: RabbitMQClient = None
message_handler: MessageHandler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global data_manager, ingestion_task, rabbitmq_client, message_handler

    logger.info("Starting Ingestion Pipeline")

    config = {
        "paperless_api_url": os.getenv("PAPERLESS_API_URL"),
        "paperless_api_token": os.getenv("PAPERLESS_API_TOKEN"),
        "vector_db_type": os.getenv("VECTOR_DB_TYPE", "chroma"),
        "chroma_url": os.getenv("CHROMA_URL", "http://localhost:8000"),
        "collection_name": os.getenv("COLLECTION_NAME", "documents"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"),
    }

    data_manager = DataManager(config)
    ingestion_task = IngestionTask(data_manager)

    # Connect to RabbitMQ
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    rabbitmq_client = RabbitMQClient(rabbitmq_url)
    connected = await rabbitmq_client.connect("ingestion")
    
    if connected:
        message_handler = MessageHandler(rabbitmq_client, ingestion_task)
        await rabbitmq_client.consume(message_handler.handle_ingestion_message)
        logger.info("RabbitMQ consumer started")
    else:
        logger.warning("RabbitMQ not available, continuing without messaging")

    yield

    if rabbitmq_client:
        await rabbitmq_client.close()

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
    return data_manager.get_status()

@app.get("/health")
async def health():
    return {
        "status": "healthy" if data_manager.is_initialized else "unhealthy",
        "service": "ingestion-pipeline"
    }

@app.post("/ingest")
async def ingest(request: IngestionRequest, background_tasks: BackgroundTasks):
    if ingestion_task.running:
        return {"status": "running", "message": "Ingestion already in progress"}

    if request.force:
        background_tasks.add_task(ingestion_task.run, force_update=True)
    else:
        background_tasks.add_task(ingestion_task.run, check_new=request.check_new)

    return {"status": "started", "message": "Ingestion started in background"}

@app.post("/ingest/sync")
async def ingest_sync(request: IngestionRequest):
    if ingestion_task.running:
        return {"status": "running", "message": "Ingestion already in progress"}

    result = ingestion_task.run(force_update=request.force, check_new=request.check_new)
    return result

@app.post("/check")
async def check_updates():
    needs_update, message = data_manager.check_for_updates()
    return {"needs_update": needs_update, "message": message}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
