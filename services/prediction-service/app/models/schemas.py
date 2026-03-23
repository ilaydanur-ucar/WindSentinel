from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime


class FeatureMessage(BaseModel):
    """
    Feature Service'in ürettiği zenginleştirilmiş veri şeması.
    feature-service/app/schemas.py → FeatureMessage ile BİREBİR eşleşmeli.
    """
    model_config = ConfigDict(extra="forbid")

    # ── Meta Bilgiler ──
    timestamp: str = Field(..., description="Ölçüm zamanı (ISO 8601)")
    asset_id: int = Field(..., description="Türbin asset numarası")
    turbine_id: str = Field(..., description="Türbin kodu (ör: WFA-T00)")
    status_type_id: int = Field(..., description="Durum tipi (0=normal)")

    # ── 6 Temel Sensör ──
    wind_speed: float = Field(..., description="Rüzgar hızı (m/s)")
    power_output: float = Field(..., description="Şebeke gücü (kW)")
    generator_rpm: float = Field(..., description="Jeneratör RPM")
    total_active_power: float = Field(..., description="Toplam aktif güç (Wh)")
    reactive_power_inductive: float = Field(..., description="İndüktif reaktif güç (kVAr)")
    reactive_power_capacitive: float = Field(..., description="Kapasitif reaktif güç (kVAr)")

    # ── Türetilmiş Özellikler (Feature Engineering) ──
    power_factor: float = Field(..., description="Güç faktörü")
    rpm_ratio: float = Field(..., description="Jeneratör / Rotor RPM oranı")
    reactive_power_balance: float = Field(..., description="Reaktif güç dengesi")
    power_to_wind_ratio: float = Field(..., description="Rüzgar hızına göre güç verimliliği")


class PredictionResult(BaseModel):
    """
    ML model tahmin sonucu. Anomali ise prediction.result kuyruğuna yollanır.
    Notification Service'in AlarmMessage şemasıyla uyumlu olmalı.
    """
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(..., description="Tahmin zamanı")
    asset_id: int = Field(..., description="Türbin asset numarası")
    turbine_id: str = Field(..., description="Türbin kodu")
    is_anomaly: bool = Field(..., description="Anomali tespit edildi mi?")
    anomaly_score: float = Field(..., description="Isolation Forest normalize skoru")
    confidence: float = Field(..., description="Hibrit model güven skoru")
    severity: str = Field(default="INFO", description="CRITICAL / WARNING / INFO")
    model_version: str = Field(..., description="Model versiyon bilgisi")
    fault_type: str = Field(default="unknown", description="Tahmin edilen hata türü")
    details: Dict[str, Any] = Field(default_factory=dict, description="Ekstra detaylar")
