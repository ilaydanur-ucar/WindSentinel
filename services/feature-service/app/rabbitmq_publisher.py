# ────────────────────────────────────────────────────────────
# rabbitmq_publisher.py — Mesaj Gönderici (Publisher) Sınıfı
# ────────────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   Bu sınıfın TEK sorumluluğu, işlenmiş (zenginleştirilmiş) FeatureMessage
#   nesnelerini alıp RabbitMQ üzerindeki hedef Exchange ve Routing Key
#   üzerinden dış dünyaya (downstream servislere) göndermektir.
#
#   İçerisinde mesaj okuma (consumer) veya işleme (engineer) mantığı YOKTUR.
# ────────────────────────────────────────────────────────────

import json
from aio_pika import Message, RobustConnection, DeliveryMode

from app.config import settings
from app.schemas import FeatureMessage
from app.logger import logger


class RabbitMQPublisher:
    """
    Feature Engineer tarafından üretilen zenginleştirilmiş verileri
    RabbitMQ üzerindeki measurement.features hedefine yazar.
    """

    def __init__(self, connection: RobustConnection):
        """
        DIP: Sınıfa somut bir RabbitMQ adresi yerine, ana Lifespan (main.py)
        tarafından kurulmuş hazır bir 'bağlantı (connection)' nesnesi enjekte edilir.
        """
        self._connection = connection
        self._channel = None
        self._exchange = None

    async def connect(self) -> None:
        """
        Kanal (Channel) ve Exchange yapısını sadece BİR KERE oluşturur (Singleton mantığı).
        Her publish işleminde kanal aç-kapa yapılmaz = Yüksek Performans.
        """
        self._channel = await self._connection.channel()

        # Exchange'i durable (kalıcı) olarak başlat/doğrula
        self._exchange = await self._channel.declare_exchange(
            name=settings.EXCHANGE_NAME,
            type="topic",
            durable=True,
        )
        logger.info(f"✅ Publisher kanalı açıldı. Exchange: {settings.EXCHANGE_NAME}")

    async def close(self) -> None:
        """Kapatma (Shutdown) sırasında kanalı güvenle iptal eder."""
        if self._channel:
            await self._channel.close()
            logger.info("Publisher kanalı kapatıldı.")

    async def publish(self, feature_msg: FeatureMessage) -> bool:
        """
        Zenginleştirilmiş FeatureMessage Pydantic modelini JSON'a çevirip
        RabbitMQ'ya fırlatır.

        Args:
            feature_msg: İşlenmiş özellik çıkış şeması

        Returns:
            Başarı durumunda True, hata durumunda False.
        """
        if not self._exchange:
            logger.error("Publisher başlatılmadı (kanal kapalı).")
            return False

        try:
            # 1. Pydantic -> DUMP (Güvenli Tip Çevirisi)
            message_body = feature_msg.model_dump_json().encode("utf-8")

            # 2. Aio-Pika Message Objesi
            msg = Message(
                body=message_body,
                delivery_mode=DeliveryMode.PERSISTENT,  # Disk'e yaz (Mesaj kaybını önle)
                content_type="application/json",
            )

            # 3. Publish - hedef Routing Key (measurement.features)
            await self._exchange.publish(
                message=msg,
                routing_key=settings.ROUTING_KEY_FEATURES
            )

            # Debug için çok konuşmasın diye sadece INFO ile genel bilgi bırakılır.
            # Yüksek yoğunluklu (Big Data) akışta sürekli terminal logu sistemi kilitler.
            return True

        except Exception as e:
            logger.error(
                f"❌ Mesaj Publish edilemedi ({feature_msg.turbine_id} - "
                f"{feature_msg.timestamp}): {e}"
            )
            return False
