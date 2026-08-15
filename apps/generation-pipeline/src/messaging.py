import json
import logging
from typing import Callable, Optional

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractQueue

logger = logging.getLogger("generation.messaging")

class RabbitMQClient:
    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self.connection = None
        self.channel: Optional[AbstractChannel] = None
        self.queue: Optional[AbstractQueue] = None
        self.exchange = None
    
    async def connect(self, queue_name: str):
        try:
            self.connection = await aio_pika.connect_robust(self.amqp_url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=1)
            
            self.exchange = await self.channel.declare_exchange(
                "paperless_ai",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            self.queue = await self.channel.declare_queue(queue_name, durable=True)
            await self.queue.bind(self.exchange, routing_key=f"pipeline.{queue_name}")
            
            logger.info(f"Connected to RabbitMQ, queue: {queue_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            return False
    
    async def publish(self, routing_key: str, message: dict):
        if not self.exchange:
            logger.error("Cannot publish, exchange not initialized")
            return
        
        try:
            await self.exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=routing_key
            )
            logger.debug(f"Published message to {routing_key}")
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
    
    async def consume(self, callback: Callable):
        if not self.queue:
            logger.error("Cannot consume, queue not initialized")
            return
        
        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    body = json.loads(message.body.decode())
                    await callback(body, message.routing_key)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
        
        await self.queue.consume(on_message)
        logger.info(f"Started consuming from queue")
    
    async def close(self):
        if self.connection:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")
