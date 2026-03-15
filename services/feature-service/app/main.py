# ────────────────────────────────────────────────────────────
# main.py — Uygulama Başlangıcı ve Yaşam Döngüsü (Lifespan)
# ────────────────────────────────────────────────────────────
#
# SRP ve BAĞIMLILIK ENJEKSİYONU (DIP):
#   - RabbitMQ Bağlantısı (Connection), Publisher ve Consumer nesneleri
#     sadece bu dosyada BİR KERE oluşturulur (Singleton) ve birbirlerine
#     enjekte edilir (Dependency Injection).
#
# EVENT-LOOP ve ASYNCIO Context Koruması (Kullanıcı İsteği):
#   - FastAPI ayağa kalkarken önce RabbitMQ bağlantısı ATANIR.
#   - Daha sonra 'asyncio.create_task' ile arkada asenkron çalışan
#     bir arka plan işi (background task) olarak dinleyici başlatılır.
#   - FastAPI kapanırken önce task durdurulur (cancel), 
#     sonra connections izole edilmiş şekilde (graceful shutdown) kapatılır.
# ────────────────────────────────────────────────────────────

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from aio_pika import connect_robust, RobustConnection

from app.config import settings
from app.logger import logger
from app.rabbitmq_publisher import RabbitMQPublisher
from app.rabbitmq_consumer import RabbitMQConsumer

# Global değişkenler (Uygulama yaşam döngüsü boyunca bir kez oluşturulup state'de tutulacak)
mq_connection: RobustConnection | None = None
publisher: RabbitMQPublisher | None = None
consumer: RabbitMQConsumer | None = None
consume_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI uygulamasının başlangıç (startup) ve kapanış (shutdown)
    süreçlerini yöneten modern (Lifespan) asenkron context yapısı.
    """
    global mq_connection, publisher, consumer, consume_task

    logger.info(f"🚀 {settings.SERVICE_NAME} başlatılıyor...")

    try:
        # 1. RabbitMQ'ya Ana (Robust) Bağlantıyı Kur
        # RobustConnection, ağ kopmalarında otomatik yeniden bağlanmayı (reconnect) dener.
        mq_connection = await connect_robust(settings.RABBITMQ_URL)

        # 2. Dependency Injection: Publisher nesnesini oluştur ve kanalı aç
        publisher = RabbitMQPublisher(connection=mq_connection)
        await publisher.connect()

        # 3. Dependency Injection: Consumer nesnesini oluştur, Publsher'ı ver ve kanalı aç
        consumer = RabbitMQConsumer(connection=mq_connection, publisher=publisher)
        await consumer.connect()

        # 4. Asenkron Tüketiciyi Başlat! (Event-Loop çakışmasını engellemek için doğru yöntem) 
        # Tüketmek bloklayıcı (blocking) bir işlem (sonsuz iterasyon) olduğu için
        # bunu doğrudan 'await consumer.consume()' diyerek YAZAMAYIZ (FastAPI kilitlenir).
        # Bunun yerine arkaplanda koşan bağımsız bir asenkron Task olarak başlatıyoruz.
        consume_task = asyncio.create_task(consumer.consume())
        
        logger.info(f"✅ {settings.SERVICE_NAME} hazır! (RabbitMQ dinleniyor...)")
        
        # ── FastAPI uygulamasını başlat (Web Sunucusu) ──
        yield  
        
    except Exception as e:
        logger.critical(f"❌ Başlangıçta Kritik Hata (RabbitMQ kapalı olabilir): {e}")
        raise e

    finally:
        # ── UYGULAMA KAPANIRKEN (Shutdown) Güvenli Çıkış (Graceful Shutdown) ──
        logger.info("🛑 Servis kapatılıyor. Kaynaklar temizlenecek...")
        
        # 1. Önce arka planda devam eden tüketim (sonsuz dinleme) işini iptal et
        if consume_task and not consume_task.done():
            consume_task.cancel()
            
        # 2. Kanal bağlantılarını kapat    
        if consumer:
            await consumer.close()
        if publisher:
            await publisher.close()
            
        # 3. Ana RabbitMQ bağlantısını kopar
        if mq_connection:
            await mq_connection.close()
            
        logger.info("✅ Tüm bağlantılar güvenle (gracefully) sonlandırıldı.")


# FastAPI uygulamasını `lifespan` kuralına bağlı olarak başlat
app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    lifespan=lifespan
)


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Docker Swarm / Kubernetes / Nginx gibi Load Balancer'ların
    "Bu servis yaşıyor mu?" sorusuna vereceği Endpoint.
    """
    state = "healthy" if mq_connection and not mq_connection.is_closed else "unhealthy"
    return {
        "service": settings.SERVICE_NAME,
        "status": state,
        "version": settings.SERVICE_VERSION,
        "consumer_active": consume_task is not None and not consume_task.done()
    }
