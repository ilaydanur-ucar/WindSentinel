from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any
from datetime import datetime

class FeatureMessage(BaseModel):
    """
    RabbitMQ'dan ('measurement.features' kuyruğundan) gelecek olan verinin şeması.
    feature-service'in ürettiği veriyi temsil eder.
    """
    model_config = ConfigDict(extra="forbid") # Güvenlik: Beklenmeyen alanları reddet (OWASP)

    timestamp: datetime = Field(..., description="Ölçümün yapıldığı zaman")
    # Aşağıdakiler feature-service'den gelecek temel feature'lara birer örnektir.
    # Gerçek feature listesine göre burası genişletilebilir.
    wind_speed: float = Field(..., description="Rüzgar Hızı (m/s)")
    active_power: float = Field(..., description="Aktif Güç (kW)")
    wind_direction: float = Field(..., description="Rüzgar Yönü (°)")
    theoretical_power_curve: float = Field(..., description="Teorik Güç Eğrisi Değeri")
    
    # feature-service'de ürettiğimiz istatistiksel / rolling özellikler
    wind_speed_rolling_mean: float = Field(..., description="Rüzgar Hızı Hareketli Ortalaması")
    wind_speed_rolling_std: float = Field(..., description="Rüzgar Hızı Standart Sapması")
    power_error: float = Field(..., description="Teorik Güç ile Aktif Güç Arasındaki Fark")


class PredictionResult(BaseModel):
    """
    Modelin tahmin sonucunu temsil eden şema.
    Eğer anomali ise 'prediction.alerts' kuyruğuna yollanacak verinin şeması.
    """
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(..., description="Ölçümün/Tahminin yapıldığı zaman")
    is_anomaly: bool = Field(..., description="Hata/Anomali tespit edildi mi?")
    anomaly_score: float = Field(..., description="Modelin anomali/güven skoru (0.0 - 1.0 arası veya -1.0 ile 1.0 arası değişebilir)")
    model_version: str = Field(..., description="Tahmini yapan modelin versiyon bilgisi")
    details: Dict[str, Any] = Field(default_factory=dict, description="Ekstra hata detayları veya feature bazlı model analizleri")
