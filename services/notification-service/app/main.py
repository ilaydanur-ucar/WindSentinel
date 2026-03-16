import asyncio
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.services.log_notifier import LogNotifier
from app.infrastructure.consumer import RabbitMQConsumer

# Log Yapılandırması
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama yaşam döngüsü yönetimi. 
    RabbitMQ Consumer asenkron bir görev olarak başlatılır.
    """
    # Notifier listesini hazırla (Strategy Pattern)
    notifiers = [LogNotifier()]
    
    # Consumer'ı başlat
    consumer = RabbitMQConsumer(notifiers)
    
    # Consumer'ı arka planda bir task olarak çalıştır
    consumer_task = asyncio.create_task(consumer.start())
    
    logger.info(f"{settings.PROJECT_NAME} başlatıldı.")
    yield
    
    # Kapanışta consumer'ı iptal et
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("Kafka Consumer durduruldu.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}
