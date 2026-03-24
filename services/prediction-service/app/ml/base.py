from abc import ABC, abstractmethod
from app.models.schemas import FeatureMessage, PredictionResult


class BasePredictor(ABC):
    """
    Tum ML modelleri icin temel (abstract) sinif.
    LSP (Liskov Substitution Principle): tum modeller bu interface'i implement eder.
    """

    @abstractmethod
    def predict(self, features: FeatureMessage) -> PredictionResult:
        pass

    def predict_with_ts(self, features: FeatureMessage, ts_features: dict) -> PredictionResult:
        """Time-series feature'li tahmin. Override edilmezse base predict kullanilir."""
        return self.predict(features)

    @abstractmethod
    def get_model_info(self) -> dict:
        pass
