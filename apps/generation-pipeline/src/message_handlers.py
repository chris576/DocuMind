import logging
from .messaging import RabbitMQClient
from .providers import BaseLLMProvider
from .models import GenerateRequest, ChatMessage

logger = logging.getLogger("generation.handlers")

class MessageHandler:
    def __init__(self, rabbitmq_client: RabbitMQClient, llm_provider: BaseLLMProvider):
        self.rabbitmq_client = rabbitmq_client
        self.llm_provider = llm_provider
    
    async def handle_generation_message(self, body: dict, routing_key: str):
        logger.info(f"Received generation message: {body}")
        
        action = body.get("action")
        
        if action == "generate":
            await self._handle_generate(body)
        elif action == "chat":
            await self._handle_chat(body)
    
    async def _handle_generate(self, body: dict):
        try:
            request = GenerateRequest(
                question=body.get("question", ""),
                context=body.get("context", ""),
                sources=body.get("sources", []),
                max_tokens=body.get("max_tokens", 1000),
                temperature=body.get("temperature", 0.7),
                stream=False
            )
            
            response = await self.llm_provider.generate(request)
            
            await self.rabbitmq_client.publish(
                "pipeline.status",
                {
                    "service": "generation-pipeline",
                    "event": "generation_complete",
                    "result": response.dict()
                }
            )
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            await self.rabbitmq_client.publish(
                "pipeline.status",
                {
                    "service": "generation-pipeline",
                    "event": "generation_failed",
                    "error": str(e)
                }
            )
    
    async def _handle_chat(self, body: dict):
        try:
            messages = [ChatMessage(**m) for m in body.get("messages", [])]
            response = await self.llm_provider.chat(messages)
            
            await self.rabbitmq_client.publish(
                "pipeline.status",
                {
                    "service": "generation-pipeline",
                    "event": "chat_complete",
                    "result": {"message": response}
                }
            )
        except Exception as e:
            logger.error(f"Chat failed: {str(e)}")
            await self.rabbitmq_client.publish(
                "pipeline.status",
                {
                    "service": "generation-pipeline",
                    "event": "chat_failed",
                    "error": str(e)
                }
            )
