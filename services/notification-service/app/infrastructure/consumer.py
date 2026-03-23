import asyncio
import json
import logging
import time
from typing import Dict, Tuple, List
import aio_pika
from app.core.config import settings
from app.models.schemas import AlarmMessage
from app.services.base import BaseNotifier

logger = logging.getLogger(__name__)

class RabbitMQConsumer:
    """
    RabbitMQ'dan anomali alarmlarını dinleyen ve Notifier'lara ileten sınıf.
    Deduplication (Cooldown) mantığını içerir.
    """
    
    def __init__(self, notifiers: List[BaseNotifier]):
        self.notifiers = notifiers
        self.connection = None
        self.channel = None
        # Deduplication cache: (asset_id, fault_type) -> last_notified_timestamp
        self._last_notified: Dict[Tuple[str, str], float] = {}

    def _should_suppress(self, alarm: AlarmMessage) -> bool:
        """Aynı alarmın cooldown süresi içinde gelip gelmediğini kontrol eder."""
        key = (alarm.turbine_id, alarm.fault_type)
        current_time = time.time()
        
        if key in self._last_notified:
            elapsed = current_time - self._last_notified[key]
            if elapsed < settings.NOTIFY_COOLDOWN_SECONDS:
                logger.debug(f"Alarm susturuldu (Cooldown): {key}. Kalan: {settings.NOTIFY_COOLDOWN_SECONDS - elapsed:.0f}s")
                return True
        
        # Cooldown bitmiş veya ilk kez geliyor
        self._last_notified[key] = current_time
        return False

    async def process_message(self, message: aio_pika.IncomingMessage):
        """Her bir RabbitMQ mesajını işleyen callback."""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                alarm = AlarmMessage(**body)
                
                # Deduplication kontrolü
                if self._should_suppress(alarm):
                    return

                # Tüm kayıtlı notifier'lara ilet
                tasks = [notifier.notify(alarm) for notifier in self.notifiers]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, res in enumerate(results):
                    if isinstance(res, Exception):
                        logger.error(f"Notifier {self.notifiers[i].__class__.__name__} hata fırlattı: {res}")
                    elif not res:
                        logger.warning(f"Notifier {self.notifiers[i].__class__.__name__} başarısız döndü.")

            except Exception as e:
                logger.error(f"Mesaj işleme hatası: {e}")

    async def start(self):
        """Consumer'ı başlatır ve kuyruğu dinlemeye başlar."""
        while True:
            try:
                self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
                self.channel = await self.connection.channel()
                
                # QoS: Bir kerede kaç mesaj işlenebilir
                await self.channel.set_qos(prefetch_count=10)
                
                queue = await self.channel.declare_queue(
                    settings.QUEUE_NAME,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": "wind.dlx",
                        "x-dead-letter-routing-key": "dlq.prediction.result",
                        "x-message-ttl": 86400000,
                    },
                )
                
                logger.info(f"Notification Service kuyruğu dinliyor: {settings.QUEUE_NAME}")
                await queue.consume(self.process_message)
                
                # Bağlantı açık olduğu sürece bekle
                await asyncio.Future()
                
            except Exception as e:
                logger.error(f"RabbitMQ bağlantı hatası, 5sn sonra tekrar denenecek: {e}")
                await asyncio.sleep(5)
            finally:
                if self.connection and not self.connection.is_closed:
                    await self.connection.close()
