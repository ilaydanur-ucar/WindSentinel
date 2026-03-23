import random
from datetime import datetime
from app.ml.base import BasePredictor
from app.models.schemas import FeatureMessage, PredictionResult


class DummyPredictor(BasePredictor):
    """
    Sistemi uçtan uca test etmek için kullanılan sahte (mock) tahmin modelidir.
    Gerçek ML modelleri yüklenemezse fallback olarak kullanılır.
    """

    def __init__(self):
        self.version = "dummy-v1.0"
        self.model_type = "mock"

    def predict(self, features: FeatureMessage) -> PredictionResult:
        """
        Basit kural tabanlı + rastgele anomali üretimi.
        Gerçek dünyada bu mantığı XGBoost/Isolation Forest yapar.
        """
        # Güç faktörü çok düşükse veya RPM oranı anormalse → anomali riski
        anomaly_hint = (
            features.power_factor < 0.1
            or features.rpm_ratio > 100
            or features.power_to_wind_ratio < -1
        )

        is_anomaly = False
        anomaly_score = random.uniform(0.1, 0.4)
        confidence = random.uniform(0.5, 0.7)

        if anomaly_hint or random.random() > 0.95:
            is_anomaly = True
            anomaly_score = random.uniform(0.65, 0.99)
            confidence = random.uniform(0.7, 0.95)

        severity = "INFO"
        if anomaly_score > 0.90:
            severity = "CRITICAL"
        elif anomaly_score > 0.63:
            severity = "WARNING"

        return PredictionResult(
            timestamp=datetime.now(),
            asset_id=features.asset_id,
            turbine_id=features.turbine_id,
            is_anomaly=is_anomaly,
            anomaly_score=round(anomaly_score, 4),
            confidence=round(confidence, 4),
            severity=severity,
            model_version=self.version,
            fault_type="generic_anomaly" if is_anomaly else "normal",
            details={
                "anomaly_hint_triggered": anomaly_hint,
                "power_factor": features.power_factor,
            }
        )

    def get_model_info(self) -> dict:
        return {
            "model_type": self.model_type,
            "version": self.version,
            "description": "Mock predictor for testing the pipeline end-to-end.",
            "status": "ready"
        }
