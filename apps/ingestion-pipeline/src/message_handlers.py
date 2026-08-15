import logging
from .messaging import RabbitMQClient
from .tasks import IngestionTask

logger = logging.getLogger("ingestion.handlers")

class MessageHandler:
    def __init__(self, rabbitmq_client: RabbitMQClient, ingestion_task: IngestionTask):
        self.rabbitmq_client = rabbitmq_client
        self.ingestion_task = ingestion_task
    
    async def handle_ingestion_message(self, body: dict, routing_key: str):
        logger.info(f"Received ingestion message: {body}")
        
        action = body.get("action")
        
        if action == "ingest":
            force = body.get("force", False)
            check_new = body.get("check_new", False)
            
            try:
                result = self.ingestion_task.run(force_update=force, check_new=check_new)
                
                # Notify status queue
                await self.rabbitmq_client.publish(
                    "pipeline.status",
                    {
                        "service": "ingestion-pipeline",
                        "event": "ingestion_complete",
                        "result": result
                    }
                )
                
                # Trigger retrieval index rebuild
                await self.rabbitmq_client.publish(
                    "pipeline.retrieval",
                    {
                        "action": "rebuild_index",
                        "source": "ingestion_complete"
                    }
                )
                
            except Exception as e:
                logger.error(f"Ingestion failed: {str(e)}")
                await self.rabbitmq_client.publish(
                    "pipeline.status",
                    {
                        "service": "ingestion-pipeline",
                        "event": "ingestion_failed",
                        "error": str(e)
                    }
                )
        
        elif action == "check_updates":
            needs_update, message = self.ingestion_task.data_manager.check_for_updates()
            await self.rabbitmq_client.publish(
                "pipeline.status",
                {
                    "service": "ingestion-pipeline",
                    "event": "update_check",
                    "needs_update": needs_update,
                    "message": message
                }
            )
