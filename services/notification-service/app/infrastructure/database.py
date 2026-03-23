import logging
import asyncpg
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    PostgreSQL async connection pool.
    Notification Service'in DB işlemleri için tek giriş noktası.
    """

    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Connection pool oluştur. Retry mantığı ile."""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                min_size=2,
                max_size=10,
                command_timeout=10,
            )
            logger.info("[DB] PostgreSQL bağlantı havuzu oluşturuldu.")
        except Exception as e:
            logger.error(f"[DB] PostgreSQL bağlantı hatası: {e}")
            raise

    async def close(self):
        """Pool'u kapat."""
        if self.pool:
            await self.pool.close()
            logger.info("[DB] PostgreSQL bağlantı havuzu kapatıldı.")

    async def insert_alert(
        self,
        turbine_id: str,
        asset_id: int,
        anomaly_type: str,
        anomaly_score: float,
        confidence: float,
    ) -> dict | None:
        """
        Alert kaydı oluştur. Dönen veri WebSocket push için kullanılır.
        Altın Kural 1: Önce DB'ye yaz, sonra bildirim yayınla.
        """
        if not self.pool:
            logger.error("[DB] Pool hazır değil, alert yazılamadı.")
            return None

        try:
            row = await self.pool.fetchrow(
                """
                INSERT INTO alerts (turbine_id, asset_id, anomaly_type, anomaly_score, confidence)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, turbine_id, asset_id, anomaly_type, anomaly_score,
                          confidence, status, created_at
                """,
                turbine_id,
                asset_id,
                anomaly_type,
                anomaly_score,
                confidence,
            )
            logger.info(f"[DB] Alert #{row['id']} kaydedildi: {turbine_id} - {anomaly_type}")
            return dict(row)
        except Exception as e:
            logger.error(f"[DB] Alert insert hatası: {e}")
            return None


# Singleton instance
db_client = DatabaseClient()
