import aio_pika
import json
import asyncio
from typing import Callable, Awaitable
from app.core.config import settings

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        retries = 5
        for i in range(retries):
            try:
                # Docker Compose ağında veya yerelde RabbitMQ URL'si
                url = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
                self.connection = await aio_pika.connect_robust(url)
                self.channel = await self.connection.channel()
                
                # Sadece anomali olan mesajlar publish edilecek queue
                await self.channel.declare_queue(settings.RABBITMQ_PUBLISH_QUEUE, durable=True)
                
                # Consume edeceğimiz (feature-service'den gelen) queue
                await self.channel.declare_queue(settings.RABBITMQ_CONSUME_QUEUE, durable=True)
                
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
        """
        Belirtilen queue'yu asenkron olarak dinler (Consumer).
        Gelen her mesajı JSON'dan Dict'e çevirir ve gönderilen `callback` fonksiyonuna paslar.
        """
        if not self.channel:
            raise RuntimeError("RabbitMQ channel is not initialized. Call connect() first.")
        
        # O(1) batch processing için Qos(prefetch_count)
        # Sistem her seferinde sadece 1 mesaj alır ve işler. Bu latency'i düşürür, bellek taşmasını önler.
        await self.channel.set_qos(prefetch_count=1)

        queue = await self.channel.declare_queue(queue_name, durable=True)
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(): # Otomatik ack/nack yönetimi aio-pika process() bloğuyla yapılır
                    try:
                        message_body = message.body.decode()
                        data_dict = json.loads(message_body)
                        # SRP: Client sadece mesajı okur/pars eder, is_mantigi bilmez, onu Orchestratora (callback'e) bırakır.
                        await callback(data_dict)
                    except json.JSONDecodeError as decode_err:
                        # Loglanabilir, geçersiz JSON parse edilemedi
                        print(f"JSON Parse Error: {decode_err} - Raw: {message_body}")
                    except Exception as e:
                        print(f"Error processing message: {e}")

    async def publish_message(self, queue_name: str, message_dict: dict):
        """
        Sadece RabbitMQ'ya mesaj gönderme (Publisher) sorumluluğu
        """
        if not self.channel:
            raise RuntimeError("RabbitMQ channel is not initialized.")
            
        message_body = json.dumps(message_dict).encode("utf-8")
        
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue_name
        )
