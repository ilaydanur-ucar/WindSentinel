# ────────────────────────────────────────────────────────────
# config.py — Ayarlar Modülü (Single Responsibility Principle)
# ────────────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   Bu dosyanın TEK sorumluluğu ortam değişkenlerini yönetmek.
#   RabbitMQ bağlantısı, CSV okuma, API endpointleri...
#   bunların hiçbiri burada yok. Sadece "ayarlar".
#
# GÜVENLİK:
#   - Şifreler ve URL'ler KOD İÇİNE yazılmaz → .env dosyasından okunur
#   - pydantic-settings ile TİP GÜVENLİĞİ sağlanır
#   - Yanlış tip verilirse uygulama başlamadan hata fırlatır
#
# DRY (Don't Repeat Yourself):
#   Tüm ayarlar tek bir yerde. 5 farklı dosyada aynı URL'yi
#   tekrar tekrar yazmak yerine settings.RABBITMQ_URL diyoruz.
# ────────────────────────────────────────────────────────────

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Ortam değişkenlerini okuyan ayarlar sınıfı.

    pydantic-settings kütüphanesi, ortam değişkenlerini
    otomatik olarak bu sınıfın alanlarına eşler ve tip kontrolü yapar.

    Örnek:
        .env →  RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672
        kod →  settings.RABBITMQ_URL  (str tipinde, doğrulanmış)
    """

    # ── RabbitMQ Ayarları ──
    RABBITMQ_URL: str = Field(
        default="amqp://admin:admin123@rabbitmq:5672",
        description="AMQP protokolü ile RabbitMQ bağlantı URL'si",
    )
    EXCHANGE_NAME: str = Field(
        default="wind.events",
        description="RabbitMQ topic exchange adı",
    )
    ROUTING_KEY: str = Field(
        default="measurement.raw",
        description="Mesajların yönlendirileceği routing key",
    )

    # ── Veri Ayarları ──
    SCADA_DATA_PATH: str = Field(
        default="/data",
        description="SCADA CSV dosyalarının bulunduğu kök dizin",
    )
    CHUNK_SIZE: int = Field(
        default=500,
        ge=1,       # minimum 1 (güvenlik: negatif değer engellemesi)
        le=10000,   # maximum 10000 (bellek koruması)
        description="Bir seferde okunacak CSV satır sayısı",
    )

    # ── Güvenlik Ayarları ──
    ALLOWED_ASSET_IDS: list[int] = Field(
        default=[0, 3, 10, 13, 14, 17, 22, 24, 25, 26, 38, 40, 42, 45, 51, 68, 69, 71, 72, 73, 84, 92],
        description="İzin verilen asset_id listesi (whitelist yaklaşımı)",
    )

    # ── Servis Bilgileri ──
    SERVICE_NAME: str = "data-ingestion-service"
    SERVICE_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"


# Singleton: Tüm uygulama boyunca tek bir settings nesnesi kullanılır
settings = Settings()
