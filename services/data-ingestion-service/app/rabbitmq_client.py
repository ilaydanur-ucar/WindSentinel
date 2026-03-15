# ──────────────────────────────────────────────────────────────
# rabbitmq_client.py — RabbitMQ Concrete Implementation (DIP)
# ──────────────────────────────────────────────────────────────
#
# DIP UYGULAMASI:
#   Bu sınıf IMessageBroker interface'ini implemente eder.
#   IngestionService bu sınıfı doğrudan bilmez,
#   sadece IMessageBroker interface'ini bilir.
#
#   IngestionService → IMessageBroker (interface)
#                           ↑
#                    RabbitMQClient (bu dosya — concrete implementation)
#
# SRP UYGULAMASI:
#   Bu dosyanın TEK sorumluluğu: RabbitMQ ile iletişim.
#   CSV okuma yok, iş mantığı yok, API yok.
#
# RabbitMQ Kavramları (Detaylı):
#
#   CONNECTION (Bağlantı):
#     TCP bağlantısı. Bir uygulama genelde TEK bir connection açar.
#     connect_robust() → bağlantı koparsa otomatik yeniden bağlanır.
#
#   CHANNEL (Kanal):
#     Connection üzerindeki sanal iletişim hattı.
#     Bir connection üzerinde birden fazla channel açılabilir.
#     Neden? → Her thread/coroutine kendi channel'ını kullanır.
#
#   EXCHANGE (Dağıtıcı):
#     Mesajların ilk ulaştığı yer. Routing key'e göre
#     hangi queue'ya gideceğine karar verir.
#     Topic exchange: Routing key pattern matching yapar.
#
#   DELIVERY MODE:
#     1 = Transient (geçici) → RAM'de, restart'ta kaybolur
#     2 = Persistent (kalıcı) → Diske yazılır, güvenli
# ──────────────────────────────────────────────────────────────

import json
import logging

import aio_pika

from app.config import settings
from app.exceptions import BrokerConnectionError, BrokerPublishError

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """
    IMessageBroker interface'inin RabbitMQ implementasyonu.

    Bu sınıf RabbitMQ'ya bağlanır ve mesaj gönderir.
    İleride farklı bir message broker kullanılacaksa
    (Kafka, Redis Streams vb.), aynı interface'i implemente
    eden yeni bir sınıf yazılır; iş mantığı değişmez.

    Kullanım:
        client = RabbitMQClient()
        await client.connect()
        await client.publish({"data": "..."})
        await client.close()
    """

    def __init__(self):
        """Başlangıç durumu: tüm bağlantılar None."""
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None
        self._exchange: aio_pika.Exchange | None = None

    async def connect(self) -> None:
        """
        RabbitMQ'ya bağlan, kanal aç ve exchange tanımla.

        Bağlantı Adımları:
            1. TCP bağlantısı kur (AMQP URL üzerinden)
            2. Channel aç (mesaj gönderme yolu)
            3. Exchange tanımla (mesaj dağıtıcısı)

        Raises:
            BrokerConnectionError: Bağlantı kurulamadı
        """
        try:
            # 1. Robust connection: bağlantı koparsa otomatik yeniden bağlanır
            self._connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL
            )
            logger.info("✅ RabbitMQ bağlantısı kuruldu")

            # 2. Channel aç
            self._channel = await self._connection.channel()

            # Publisher confirms: Mesajın RabbitMQ'ya ulaştığının onayı
            # Bu olmadan mesaj gönderildi mi bilemeyiz
            await self._channel.set_qos(prefetch_count=1)
            logger.info("✅ AMQP kanalı açıldı")

            # 3. Exchange tanımla (idempotent: varsa mevcut olanı kullanır)
            self._exchange = await self._channel.declare_exchange(
                settings.EXCHANGE_NAME,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            logger.info(
                f"✅ Exchange hazır: {settings.EXCHANGE_NAME} (topic, durable)"
            )

        except Exception as e:
            logger.error(f"❌ RabbitMQ bağlantı hatası: {e}")
            raise BrokerConnectionError(
                message="Mesaj kuyruğu sistemi bağlantısı kurulamadı.",
                detail=str(e),
            )

    async def publish(self, message: dict) -> bool:
        """
        Mesajı RabbitMQ'ya publish et.

        Mesaj Akışı:
            Python dict → JSON string → UTF-8 bytes → AMQP Message → Exchange

        Args:
            message: Gönderilecek veri (dict)

        Returns:
            True → başarılı, False → başarısız

        Raises:
            BrokerPublishError: Mesaj gönderilemedi
        """
        if not self._exchange:
            raise BrokerPublishError(
                message="Mesaj gönderilemedi: Bağlantı yok.",
                detail="Exchange tanımlı değil, connect() çağrılmalı",
            )

        try:
            # dict → JSON string → bytes
            body = json.dumps(message, default=str).encode("utf-8")

            # AMQP mesajı oluştur
            amqp_message = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )

            # Exchange'e yayınla
            await self._exchange.publish(
                amqp_message,
                routing_key=settings.ROUTING_KEY,
            )
            return True

        except Exception as e:
            logger.error(f"❌ Mesaj publish hatası: {e}")
            return False

    async def close(self) -> None:
        """
        Bağlantıyı düzgün kapat.

        Neden önemli?
        → Açık bırakılan bağlantılar sunucu kaynaklarını tüketir
        → Docker container kapanırken graceful shutdown için gerekli
        """
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("✅ RabbitMQ bağlantısı kapatıldı")

    @property
    def is_connected(self) -> bool:
        """Bağlantının aktif olup olmadığını kontrol et."""
        return (
            self._connection is not None
            and not self._connection.is_closed
        )
