from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "WindSentinel-Notification-Service"
    
    # RabbitMQ Ayarları
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    QUEUE_NAME: str = "prediction.alerts"
    
    # Deduplication (Cooldown) Ayarları
    # Aynı asset_id ve fault_type için bildirimler arası bekleme süresi (saniye)
    NOTIFY_COOLDOWN_SECONDS: int = 300  # 5 Dakika
    
    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
