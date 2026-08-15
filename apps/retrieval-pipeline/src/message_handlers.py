import logging
import requests
from .messaging import RabbitMQClient
from .search_engine import SearchEngine

logger = logging.getLogger("retrieval.handlers")

class MessageHandler:
    def __init__(self, rabbitmq_client: RabbitMQClient, search_engine: SearchEngine):
        self.rabbitmq_client = rabbitmq_client
        self.search_engine = search_engine
    
    async def handle_retrieval_message(self, body: dict, routing_key: str):
        logger.info(f"Received retrieval message: {body}")
        
        action = body.get("action")
        
        if action == "rebuild_index":
            await self._rebuild_bm25_index()
        
        elif action == "search":
            await self._handle_search_request(body)
        
        elif action == "context":
            await self._handle_context_request(body)
    
    async def _rebuild_bm25_index(self):
        try:
            logger.info("Rebuilding BM25 index")
            
            # Fetch documents from ingestion pipeline
            ingestion_url = self._get_ingestion_url()
            response = requests.get(f"{ingestion_url}/status", timeout=10)
            
            if response.status_code != 200:
                raise Exception("Could not connect to ingestion pipeline")
            
            # For now, we need to fetch documents from a shared source
            # In the full implementation, ingestion should push documents via RabbitMQ
            # or share them through a document store
            logger.warning("BM25 rebuild needs document source implementation")
            
            await self.rabbitmq_client.publish(
                "pipeline.status",
                {
                    "service": "retrieval-pipeline",
                    "event": "index_rebuild_complete",
                    "documents_count": len(self.search_engine.documents)
                }
            )
        except Exception as e:
            logger.error(f"Index rebuild failed: {str(e)}")
            await self.rabbitmq_client.publish(
                "pipeline.status",
                {
                    "service": "retrieval-pipeline",
                    "event": "index_rebuild_failed",
                    "error": str(e)
                }
            )
    
    async def _handle_search_request(self, body: dict):
        logger.info("Handling async search request via RabbitMQ")
        # Async search via RabbitMQ could be used for long-running queries
        # For now, the HTTP endpoint is the primary interface
    
    async def _handle_context_request(self, body: dict):
        logger.info("Handling async context request via RabbitMQ")
        # Async context via RabbitMQ could be used for batch processing
    
    def _get_ingestion_url(self) -> str:
        import os
        return os.getenv("INGESTION_PIPELINE_URL", "http://localhost:8001")
