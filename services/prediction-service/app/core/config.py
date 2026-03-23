import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "WindSentinel Prediction Service"
    DEBUG: bool = False

    # RabbitMQ Ayarları
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    
    # Kuyruk İsimleri (definitions.json ile eşleşmeli)
    RABBITMQ_CONSUME_QUEUE: str = "measurement.featured"
    RABBITMQ_PUBLISH_QUEUE: str = "prediction.result"

    # Model Ayarları
    MODEL_TYPE: str = os.getenv("MODEL_TYPE", "dummy") # dummy, xgboost, isolation_forest vb.
    MODEL_PATH: str = os.getenv("MODEL_PATH", "") # Gerçek model .pkl yolu (ileride)
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
