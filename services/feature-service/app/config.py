# ────────────────────────────────────────────────────────────
# config.py — Ayarlar Modülü (Single Responsibility Principle)
# ────────────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   Bu dosyanın TEK sorumluluğu ortam değişkenlerini ve
#   sabitleri (RabbitMQ bağlantısı, Kuyruk/Exchange adları, DLX, QoS)
#   yönetmektir. İş mantığı yoktur.
#
# GÜVENLİK VE TUTARLILIK:
#   - Şifreler ve URL'ler kod içine yazılmaz (.env dosyasından çekilir)
#   - pydantic-settings ile tip güvenliği (type safety) sağlanır.
# ────────────────────────────────────────────────────────────

from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Feature Service yapılandırma ayarları sınıfı.
    pydantic-settings kütüphanesi ortam değişkenlerini bu sınıfın
    alanlarına otomatik bağlar ve tiplerini kontrol eder.
    """

    # ── RabbitMQ Bağlantı ──
    RABBITMQ_URL: str = Field(
        default="",
        description="AMQP protokolü ile RabbitMQ bağlantı URL'si",
    )
    
    # ── Exchange ve Akış Ayarları (Giriş / Çıkış) ──
    EXCHANGE_NAME: str = Field(
        default="wind.events",
        description="Mesajların ortak dağıtım exchange adı",
    )
    
    # DINLENECEK KUYRUK (Input: Raw Data)
    ROUTING_KEY_RAW: str = Field(
        default="measurement.raw",
        description="Dinlenecek ham veri routing key'i",
    )
    QUEUE_RAW: str = Field(
        default="measurement.raw",
        description="Data Ingestion servisinden gelen ham veri kuyruğu",
    )
    
    # GÖNDERİLECEK KUYRUK (Output: Featured Data)
    ROUTING_KEY_FEATURES: str = Field(
        default="measurement.featured",
        description="Zenginleştirilmiş verinin gönderileceği routing key",
    )
    QUEUE_FEATURES: str = Field(
        default="measurement.featured",
        description="Zenginleştirilmiş verilerin birikeceği kuyruk",
    )
    
    # ── Dead-Letter Exchange (DLX) Ayarları ──
    DLX_EXCHANGE_NAME: str = Field(
        default="wind.dlx",
        description="Hatalı mesajların düşeceği dead-letter exchange",
    )
    DLX_QUEUE: str = Field(
        default="dlq.measurement.raw",
        description="Hatalı mesajların birikeceği dead-letter queue",
    )
    DLX_ROUTING_KEY: str = Field(
        default="dlq.measurement.raw",
        description="Dead-letter yönlendirme key'i",
    )

    # ── Consumer İş Mantığı Ayarları ──
    PREFETCH_COUNT: int = Field(
        default=100,
        ge=1,
        description="Aynı anda bellekte tutulacak/islenen (unacked) maksimum mesaj sayısı (QoS)",
    )
    MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        description="Mesaj hataya düştüğünde yapılacak maksimum yeniden deneme sayısı",
    )

    # ── Servis Bilgileri ──
    SERVICE_NAME: str = "feature-service"
    SERVICE_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"

# Uygulama genelinde kullanılacak Singleton nesne
settings = Settings()
