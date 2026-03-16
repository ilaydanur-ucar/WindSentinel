import random
from app.ml.base import BasePredictor
from app.models.schemas import FeatureMessage, PredictionResult

class DummyPredictor(BasePredictor):
    """
    Sistemi uçtan uca test etmek için kullanılan sahte (mock) tahmin modelidir.
    Gerçek bir makine öğrenmesi modeli yüklenene kadar bu sınıf kullanılacaktır.
    """

    def __init__(self):
        self.version = "dummy-v1.0"
        self.model_type = "mock"
        # Gerçek modeller init anında (startup'ta) 1 kere .pkl'den yüklenecektir.

    def predict(self, features: FeatureMessage) -> PredictionResult:
        # Pydantic'ten gelen feature'ları okuyarak çok basit/rastgele bir mantık kuralım
        
        # Power error (Aktif güç ile teorik arasındaki fark) çok yüksekse
        # anomali (arıza) riskini yüksek sayalım. 
        # (Gerçek dünyada bu mantığı XGBoost/Isolation Forest yapar)
        error_ratio = 0.0
        if features.theoretical_power_curve > 0:
            error_ratio = abs(features.power_error) / features.theoretical_power_curve
            
        # Rastgelelik veya eşik değer bazlı anomali üret
        # Örnek: Teorik üretilmesi gerekenden %30 sapma varsa veya random() > 0.95 ise anomali olsun
        is_anomaly = False
        anomaly_score = random.uniform(0.1, 0.4) # Normal skor
        
        if error_ratio > 0.30 or random.random() > 0.95:
            is_anomaly = True
            anomaly_score = random.uniform(0.75, 0.99) # Yüksek risk skoru

        return PredictionResult(
            timestamp=features.timestamp,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            model_version=self.version,
            details={
                "error_ratio_triggered": error_ratio > 0.30,
                "calculated_error_ratio": round(error_ratio, 4)
            }
        )

    def get_model_info(self) -> dict:
        """
        O an aktif olan model hakkında bilgi verir.
        Endpoint (/model/info) tarafından çağrılacaktır.
        """
        return {
            "model_type": self.model_type,
            "version": self.version,
            "description": "This is a mock predictor for testing the pipeline end-to-end.",
            "status": "ready"
        }
