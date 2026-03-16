from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Dict, Any, Optional

class AlarmMessage(BaseModel):
    """
    Prediction Service'den gelen anomali alarmının şeması.
    """
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(..., description="Anomali tespit zamanı")
    is_anomaly: bool = Field(..., description="Anomali durumu (True)")
    anomaly_score: float = Field(..., description="Model skoru")
    confidence: float = Field(..., description="Hibrit model güven skoru")
    severity: str = Field(..., description="Ciddiyet Seviyesi (CRITICAL, WARNING, INFO)")
    model_version: str = Field(..., description="Model sürümü")
    fault_type: str = Field(..., description="Hata türü")
    asset_id: Optional[str] = Field(None, description="Hangi türbinden geldiği (Opsiyonel)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Ek detaylar")
