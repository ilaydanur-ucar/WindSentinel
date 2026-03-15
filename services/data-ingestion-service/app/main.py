# ──────────────────────────────────────────────────────────────
# main.py — Uygulama Giriş Noktası (SRP — Minimal)
# ──────────────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   main.py mümkün olduğunca KÜÇÜK tutulur.
#   Sorumluluğu sadece:
#     1. Logging ayarla
#     2. FastAPI uygulamasını oluştur
#     3. Yaşam döngüsünü yönet (startup/shutdown)
#     4. Router'ı ekle
#
#   İş mantığı → ingestion_service.py
#   Route'lar → routes.py
#   Bağımlılıklar → dependencies.py
# ──────────────────────────────────────────────────────────────

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routes import router
from app.dependencies import get_rabbitmq_client

# ──────────────────────────────────────────────────────
# Logging Ayarları
# ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("data-ingestion")


# ──────────────────────────────────────────────────────
# Lifespan — Uygulama Başlangıç / Bitiş Yönetimi
# ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama yaşam döngüsü:
        yield öncesi → uygulama BAŞLARKEN çalışır
        yield sonrası → uygulama KAPANIRKEN çalışır
    """
    # ── BAŞLANGIÇ ──
    logger.info("🚀 Data Ingestion Service başlıyor...")
    logger.info(f"   RabbitMQ: {settings.RABBITMQ_URL}")
    logger.info(f"   SCADA Path: {settings.SCADA_DATA_PATH}")

    client = get_rabbitmq_client()

    # RabbitMQ bağlantısı (retry mekanizması)
    for attempt in range(10):
        try:
            await client.connect()
            break
        except Exception as e:
            logger.warning(f"⏳ RabbitMQ denemesi {attempt + 1}/10: {e}")
            await asyncio.sleep(3)
    else:
        logger.error("❌ RabbitMQ'ya bağlanılamadı! Servis yine de başlayacak.")

    logger.info("✅ Data Ingestion Service hazır!")
    yield

    # ── KAPANIŞ ──
    logger.info("🛑 Kapanıyor...")
    await client.close()
    logger.info("👋 Güle güle!")


# ──────────────────────────────────────────────────────
# FastAPI Uygulaması
# ──────────────────────────────────────────────────────
app = FastAPI(
    title="WindSentinel — Data Ingestion Service",
    description="SCADA CSV verilerini okuyarak RabbitMQ'ya publish eder.",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)

# Router'ı ekle (tüm endpoint'ler routes.py'den gelir)
app.include_router(router)
