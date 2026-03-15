# ────────────────────────────────────────────────────────────
# rabbitmq_consumer.py — Mesaj Tüketici ve Hata Yönetimi Sınıfı
# ────────────────────────────────────────────────────────────
#
# SRP ve HATA YÖNETİMİ UYGULAMASI (Kullanıcı İsteği):
#   - x-death Header: Mesajın kuyruktan rededilme (reject) sayısını öğrenir.
#   - DLX (Dead-Letter Exchange): Maksimum deneme (MAX_RETRIES) aşılırsa,
#     mesaja NACK (requeue=False) göndererek onu doğrudan DLX kuyruğuna atar.
#   - ACK/NACK: Başarılı durumlarda ACK, anlık/geçici hatalarda REQUEUE edilir.
# ────────────────────────────────────────────────────────────

import json
from aio_pika import IncomingMessage, RobustConnection
from aio_pika.abc import AbstractRobustQueue
from pydantic import ValidationError

from app.config import settings
from app.schemas import RawMeasurementMessage
from app.feature_engineer import FeatureEngineer
from app.rabbitmq_publisher import RabbitMQPublisher
from app.logger import logger


class RabbitMQConsumer:
    """
    RabbitMQ üzerindeki (measurement.raw) isimli kuyruğu dinleyerek
    içerisinden akan devasa ham CSV mesajlarını satır satır havada kapar.
    Yakalanan veriler Stateless (Durumsuz) FeatureEngineer ile zenginleştirilir.
    """

    def __init__(self, connection: RobustConnection, publisher: RabbitMQPublisher):
        self._connection = connection
        self._publisher = publisher
        self._channel = None
        self._queue: AbstractRobustQueue = None

    async def connect(self) -> None:
        """
        Sınıfı ayağa kaldıran ana metot. 
        Kuyruğu, DLX Exchange'ini ve x-dead-letter yönlendirmelerini ayarlar.
        """
        self._channel = await self._connection.channel()
        
        # Prefetch (QoS): Aynı anda bellekte kaç mesaj tutulacak
        await self._channel.set_qos(prefetch_count=settings.PREFETCH_COUNT)

        # 1. DLX (Ölü Harf) Exchange'ini Oluştur
        dlx_exchange = await self._channel.declare_exchange(
            name=settings.DLX_EXCHANGE_NAME,
            type="topic",
            durable=True
        )
        
        # 1.1 DLX Kuyruğunu Oluştur ve Bağla
        dlx_queue = await self._channel.declare_queue(
            name=settings.DLX_QUEUE,
            durable=True
        )
        await dlx_queue.bind(exchange=dlx_exchange, routing_key=settings.DLX_ROUTING_KEY)

        # 2. ANA Exchange ve Kuyruğu Oluştur
        main_exchange = await self._channel.declare_exchange(
            name=settings.EXCHANGE_NAME,
            type="topic",
            durable=True
        )
        
        # 2.1 Ana kuyruğa DLX kurallarını (Dead-Letter Kuralları) veriyoruz!
        # Böylece nack/reject alan her mesaj otomatik olarak belirlediğimiz DLX'e düşecek.
        queue_arguments = {
            "x-dead-letter-exchange": settings.DLX_EXCHANGE_NAME,
            "x-dead-letter-routing-key": settings.DLX_ROUTING_KEY,
            "x-message-ttl": 86400000
        }
        
        self._queue = await self._channel.declare_queue(
            name=settings.QUEUE_RAW,
            durable=True,
            arguments=queue_arguments
        )
        await self._queue.bind(exchange=main_exchange, routing_key=settings.ROUTING_KEY_RAW)
        
        logger.info(
            f"✅ Consumer kanalı açıldı ve {settings.QUEUE_RAW} dinlenmeye hazır (Prefetch: {settings.PREFETCH_COUNT})."
        )

    async def consume(self) -> None:
        """Sonsuz döngüde asenkron (iterative) olarak RabbitMQ'dan mesajları yutar."""
        if not self._queue:
            raise RuntimeError("Consumer başlatılmamış. Lütfen connect() çağırın.")

        logger.info("🎧 Mesaj dinleniyor...")
        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                await self._process_message(message)

    async def _process_message(self, message: IncomingMessage) -> None:
        """
        Gelen her mesajın işlendiği, ACK/NACK (Acknowledgement) bloklarının 
        ve x-death Header okumalarının yapıldığı ana merkez.
        """
        # 1. x-death header kontrolü (Kaç kez DLX/Redelivered döngüsüne girdi)
        retry_count = 0
        if message.headers and "x-death" in message.headers:
            try:
                # RabbitMQ x-death'i bir List-Of-Dictionaries olarak saklar.
                # 'count' özelliği bu mesajın DLX/Requeue çevriminden kaç kez geçtiğini gösterir.
                retry_count = message.headers["x-death"][0]["count"]
            except (IndexError, KeyError):
                pass
        
        # İki alternatif okuma (Eğer x-death kullanılmayan düz requeue durumu varsa redelivered sayacı)
        elif message.redelivered:
            retry_count += 1 

        try:
            # Body -> String -> Dict
            body_str = message.body.decode("utf-8")
            raw_dict = json.loads(body_str)
            
            # Pydantic Tip Koruması (Schema Validation)
            raw_msg = RawMeasurementMessage(**raw_dict)

            # İş Mantığı (Point-Anomaly, Stateless Feature Engineering)
            feature_msg = FeatureEngineer.process(raw_msg)
            
            # Üretilen Veriyi Yeni Havuza (measurement.features) Fırlat
            is_published = await self._publisher.publish(feature_msg)
            
            if is_published:
                # ==========================================
                # ✅ BAŞARILI İŞLEM (Mesajı kalıcı olarak sil)
                # ==========================================
                await message.ack()
            else:
                raise Exception("Publisher hedefe (" + settings.ROUTING_KEY_FEATURES + ") yazamadı.")

        except (ValidationError, json.JSONDecodeError) as parse_error:
            # GÜVENLİK (Pydantic / JSON Hatası)
            # Eğer hacker payload değiştirdiyse veya format bozuksa, bu tekrar denenerek 
            # düzeltilebilecek bir hata değildir.
            logger.error(
                f"❌ Şema doğrulama (Validation/Format) hatası! Mesaj doğrudan reddedildi (DLX'e düşüyor): {parse_error}"
            )
            # ==========================================
            # 🚨 DOĞRUDAN DLX (requeue=False)
            # ==========================================
            await message.nack(requeue=False)

        except Exception as e:
            # BEKLENMEYEN / GEÇİCİ İş mantığı, publisher veya network hataları
            if retry_count < settings.MAX_RETRIES:
                logger.warning(
                    f"⚠️ İşlem geçici hataya düştü, requeue ediliyor ({retry_count + 1}/{settings.MAX_RETRIES}): {e}"
                )
                # ==========================================
                # 🔄 RETRY (Mesajı kuyruğa yeniden al)
                # ==========================================
                await message.reject(requeue=True)
            else:
                logger.error(
                    f"🚨 Mesaj {settings.MAX_RETRIES} kez işlenemedi! DLX'e (Dead-Letter) düşürülüyor. Hata: {e}"
                )
                # ==========================================
                # 🚨 3. RETRY SONRASI DLX (requeue=False)
                # ==========================================
                await message.nack(requeue=False)

    async def close(self) -> None:
        """Uygulama kapanırken (Lifespan bitişinde) kanalı güvenle kapatır."""
        if self._channel:
            await self._channel.close()
            logger.info("Consumer kanalı kapatıldı.")
