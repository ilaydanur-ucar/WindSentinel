from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Dict, Any


class AlarmMessage(BaseModel):
    """
    Prediction Service'den gelen anomali alarmının şeması.
    prediction-service/app/models/schemas.py → PredictionResult ile BİREBİR eşleşmeli.
    """
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(..., description="Anomali tespit zamanı")
    asset_id: int = Field(..., description="Türbin asset numarası")
    turbine_id: str = Field(..., description="Türbin kodu (ör: WFA-T00)")
    is_anomaly: bool = Field(..., description="Anomali durumu")
    anomaly_score: float = Field(..., description="Isolation Forest normalize skoru")
    confidence: float = Field(..., description="Hibrit model güven skoru")
    severity: str = Field(default="INFO", description="CRITICAL / WARNING / INFO")
    model_version: str = Field(..., description="Model sürümü")
    fault_type: str = Field(default="unknown", description="Hata türü")
    details: Dict[str, Any] = Field(default_factory=dict, description="Ek detaylar")
