import json
import logging
import aio_pika
from app.services.base import BaseNotifier
from app.models.schemas import AlarmMessage
from app.infrastructure.database import db_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseNotifier(BaseNotifier):
    """
    Anomali alarmlarını PostgreSQL'e kaydeden ve
    API Gateway'e WebSocket push için RabbitMQ mesajı gönderen notifier.

    Altın Kural 1: Önce DB insert, başarılıysa RabbitMQ publish.
    Altın Kural 2: Duplicate kontrolü Consumer seviyesinde (cooldown) yapılır.
    """

    def __init__(self):
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None

    async def _ensure_channel(self):
        """RabbitMQ publish kanalını hazırla (lazy init)."""
        if self._channel is None or self._channel.is_closed:
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self._channel = await self._connection.channel()

    async def notify(self, alarm: AlarmMessage) -> bool:
        """
        1. DB'ye alert yaz
        2. Başarılıysa → API Gateway'e RabbitMQ ile bildir (WebSocket push)
        """
        try:
            # Sadece anomali olanları kaydet
            if not alarm.is_anomaly:
                return True

            # Adım 1: DB'ye yaz (Altın Kural 1)
            alert_record = await db_client.insert_alert(
                turbine_id=alarm.asset_id or "UNKNOWN",
                asset_id=int(alarm.asset_id) if alarm.asset_id and alarm.asset_id.isdigit() else 0,
                anomaly_type=alarm.fault_type,
                anomaly_score=alarm.anomaly_score,
                confidence=alarm.confidence,
            )

            if alert_record is None:
                logger.error("[DB_NOTIFIER] DB insert başarısız, WebSocket publish atlanıyor.")
                return False

            # Adım 2: API Gateway'e bildir (WebSocket push tetiklemesi)
            await self._publish_alert_event(alert_record)

            return True

        except Exception as e:
            logger.error(f"[DB_NOTIFIER] Hata: {e}")
            return False

    async def _publish_alert_event(self, alert_record: dict):
        """
        alert.notify routing key ile API Gateway'e mesaj gönder.
        Gateway bunu alıp Socket.IO ile client'lara push edecek.
        """
        try:
            await self._ensure_channel()

            exchange = await self._channel.get_exchange(settings.ALERT_NOTIFY_EXCHANGE)

            # Datetime'ı JSON serializable yap
            payload = {
                "id": alert_record["id"],
                "turbine_id": alert_record["turbine_id"],
                "asset_id": alert_record["asset_id"],
                "anomaly_type": alert_record["anomaly_type"],
                "anomaly_score": alert_record["anomaly_score"],
                "confidence": alert_record["confidence"],
                "status": alert_record["status"],
                "created_at": alert_record["created_at"].isoformat(),
            }

            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    content_type="application/json",
                ),
                routing_key=settings.ALERT_NOTIFY_ROUTING_KEY,
            )

            logger.info(f"[DB_NOTIFIER] Alert #{alert_record['id']} → API Gateway'e bildirildi.")

        except Exception as e:
            # WebSocket push başarısız olsa bile DB kaydı var - sistem tutarlı
            logger.warning(f"[DB_NOTIFIER] RabbitMQ publish hatası (DB kaydı mevcut): {e}")
