import aio_pika
import json
import asyncio
from typing import Callable, Awaitable
from app.core.config import settings


# definitions.json ile eşleşen queue argümanları
QUEUE_ARGS = {
    "measurement.featured": {
        "x-dead-letter-exchange": "wind.dlx",
        "x-dead-letter-routing-key": "dlq.measurement.featured",
        "x-message-ttl": 86400000,
    },
    "prediction.result": {
        "x-dead-letter-exchange": "wind.dlx",
        "x-dead-letter-routing-key": "dlq.prediction.result",
        "x-message-ttl": 86400000,
    },
}

EXCHANGE_NAME = "wind.events"


class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self._exchange = None

    async def connect(self):
        retries = 5
        for i in range(retries):
            try:
                url = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
                self.connection = await aio_pika.connect_robust(url)
                self.channel = await self.connection.channel()

                # Exchange (topic) - diğer servislerle tutarlı
                self._exchange = await self.channel.declare_exchange(
                    EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
                )

                # Consume queue (measurement.featured - DLX argümanlarıyla)
                consume_args = QUEUE_ARGS.get(settings.RABBITMQ_CONSUME_QUEUE, {})
                await self.channel.declare_queue(
                    settings.RABBITMQ_CONSUME_QUEUE,
                    durable=True,
                    arguments=consume_args,
                )

                # Publish queue (prediction.result - DLX argümanlarıyla)
                publish_args = QUEUE_ARGS.get(settings.RABBITMQ_PUBLISH_QUEUE, {})
                await self.channel.declare_queue(
                    settings.RABBITMQ_PUBLISH_QUEUE,
                    durable=True,
                    arguments=publish_args,
                )

                print(f"RabbitMQ Connection Successful. Connected to {settings.RABBITMQ_HOST}")
                return
            except Exception as e:
                print(f"RabbitMQ connection failed (Attempt {i+1}/{retries}): {e}")
                await asyncio.sleep(5)
        raise ConnectionError("Could not connect to RabbitMQ after multiple attempts.")

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            print("RabbitMQ connection closed.")

    async def consume_messages(self, queue_name: str, callback: Callable[[dict], Awaitable[None]]):
        """Belirtilen queue'yu asenkron olarak dinler (Consumer)."""
        if not self.channel:
            raise RuntimeError("RabbitMQ channel is not initialized. Call connect() first.")

        await self.channel.set_qos(prefetch_count=1)

        queue_args = QUEUE_ARGS.get(queue_name, {})
        queue = await self.channel.declare_queue(
            queue_name, durable=True, arguments=queue_args
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        message_body = message.body.decode()
                        data_dict = json.loads(message_body)
                        await callback(data_dict)
                    except json.JSONDecodeError as decode_err:
                        print(f"JSON Parse Error: {decode_err} - Raw: {message_body}")
                    except Exception as e:
                        print(f"Error processing message: {e}")

    async def publish_message(self, routing_key: str, message_dict: dict):
        """wind.events exchange üzerinden mesaj publish eder (topic exchange)."""
        if not self._exchange:
            raise RuntimeError("RabbitMQ exchange is not initialized.")

        message_body = json.dumps(message_dict).encode("utf-8")

        await self._exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=routing_key,
        )
