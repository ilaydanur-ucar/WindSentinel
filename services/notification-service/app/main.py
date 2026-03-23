import asyncio
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.services.log_notifier import LogNotifier
from app.services.db_notifier import DatabaseNotifier
from app.infrastructure.consumer import RabbitMQConsumer
from app.infrastructure.database import db_client

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
    1. PostgreSQL bağlantısı kur
    2. Notifier'ları hazırla (Strategy Pattern)
    3. RabbitMQ Consumer'ı arka planda başlat
    """
    # PostgreSQL bağlantısı
    await db_client.connect()

    # Notifier listesi (Strategy Pattern - yeni kanal eklemek kolay)
    notifiers = [
        LogNotifier(),
        DatabaseNotifier(),
    ]

    # Consumer'ı başlat
    consumer = RabbitMQConsumer(notifiers)
    consumer_task = asyncio.create_task(consumer.start())

    logger.info(f"{settings.PROJECT_NAME} başlatıldı. Notifiers: {[n.__class__.__name__ for n in notifiers]}")
    yield

    # Kapanışta temizlik
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("RabbitMQ Consumer durduruldu.")

    await db_client.close()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


@app.get("/health")
async def health_check():
    db_ok = db_client.pool is not None and not db_client.pool._closed
    return {
        "status": "ok" if db_ok else "degraded",
        "service": settings.PROJECT_NAME,
        "db": "connected" if db_ok else "disconnected",
    }
