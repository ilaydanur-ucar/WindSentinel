from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "WindSentinel-Notification-Service"

    # RabbitMQ Ayarları
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    QUEUE_NAME: str = "prediction.result"

    # Alert bildirim kuyruğu (API Gateway WebSocket push için)
    ALERT_NOTIFY_EXCHANGE: str = "wind.events"
    ALERT_NOTIFY_ROUTING_KEY: str = "alert.notify"

    # PostgreSQL Ayarları (değerler docker-compose environment'tan gelir)
    DB_HOST: str = os.getenv("DB_HOST", "postgres")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "windsentinel")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # Deduplication (Cooldown) Ayarları
    # Aynı asset_id ve fault_type için bildirimler arası bekleme süresi (saniye)
    NOTIFY_COOLDOWN_SECONDS: int = 300  # 5 Dakika

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
