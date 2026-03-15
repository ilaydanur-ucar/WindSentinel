# ──────────────────────────────────────────────────────
# schemas.py — Pydantic Veri Modelleri (SRP + Güvenlik)
# ──────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   Bu dosyanın TEK sorumluluğu veri şekillerini (schema)
#   tanımlamak. İstek/yanıt formatları burada.
#
# GÜVENLİK (A04:2021 — Insecure Design):
#   Pydantic modeller otomatik olarak:
#   - Tip kontrolü yapar (string yerine int bekleniyor → hata)
#   - Aralık kontrolü yapar (ge=0 → negatif değer kabul etmez)
#   - Fazla alanları reddeder (forbid → SQL injection denemelerini engeller)
#
# DRY UYGULAMASI:
#   Mesaj formatı bir kez tanımlanır, hem CSV dönüşümünde
#   hem API yanıtında aynı model kullanılır.
# ──────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from datetime import datetime


class MeasurementMessage(BaseModel):
    """
    RabbitMQ'ya gönderilecek ölçüm mesajının formatı.

    Bu model, CSV'den okunan her satırın dönüştürüleceği formattır.
    API kontratındaki 'measurement.raw' mesaj yapısına uyar.

    Güvenlik: Tüm alanlar tipli ve sınırlıdır.
    """

    # ── Meta Bilgiler ──
    timestamp: str = Field(
        ...,  # ... = zorunlu alan
        description="Ölçüm zamanı (ISO 8601 formatı)",
        examples=["2021-08-03T06:10:00"],
    )
    asset_id: int = Field(
        ...,
        ge=0,  # >= 0 (negatif değer engellenir)
        description="Türbin asset numarası",
    )
    turbine_id: str = Field(
        ...,
        min_length=1,
        max_length=20,  # Fazla uzun string engellenir (buffer overflow koruması)
        description="Türbin kodu (ör: WFA-T00)",
    )
    status_type_id: int = Field(
        ...,
        ge=0,
        description="Durum tipi (0=normal, diğerleri=arıza)",
    )

    # ── 6 Seçilmiş Feature ──
    wind_speed: float = Field(..., description="Rüzgar hızı (m/s)")
    power_output: float = Field(..., description="Şebeke gücü (kW)")
    generator_rpm: float = Field(..., description="Jeneratör RPM")
    total_active_power: float = Field(..., description="Toplam aktif güç (Wh)")
    reactive_power_inductive: float = Field(..., description="İndüktif reaktif güç (kVAr)")
    reactive_power_capacitive: float = Field(..., description="Kapasitif reaktif güç (kVAr)")

    # ── Ek Sensörler ──
    rotor_rpm: float = Field(..., description="Rotor RPM")
    gearbox_oil_temp: float = Field(..., description="Dişli kutusu yağ sıcaklığı (°C)")

    class Config:
        # Tanımlanmamış extra alanları REDDET (güvenlik)
        # Saldırgan ek alanlar göndermeye çalışırsa hata verir
        extra = "forbid"


class IngestRequest(BaseModel):
    """
    POST /ingest isteğinin formatı.

    Güvenlik: asset_id tip ve aralık kontrolü Pydantic ile yapılır.
    Ek kontroller (whitelist) security.py'de yapılır.
    """
    asset_id: int = Field(
        ...,
        ge=0,
        description="İşlenecek türbin ID'si",
        examples=[0],
    )

    class Config:
        extra = "forbid"  # Fazla alan gönderilmesini engelle


class IngestResponse(BaseModel):
    """POST /ingest yanıtının formatı."""
    status: str
    asset_id: int
    messages_sent: int
    message: str


class HealthResponse(BaseModel):
    """GET /health yanıtının formatı."""
    status: str
    service: str
    version: str
    rabbitmq_connected: bool
    timestamp: str


class StatusResponse(BaseModel):
    """GET /status yanıtının formatı."""
    total_messages_sent: int
    total_files_processed: int
    is_running: bool
    current_file: str | None
    last_run: str | None
    rabbitmq_connected: bool


class DatasetInfo(BaseModel):
    """Tek bir CSV dosyasının bilgileri."""
    asset_id: int
    filename: str
    path: str
    size_mb: float
