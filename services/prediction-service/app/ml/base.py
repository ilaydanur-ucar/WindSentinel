from abc import ABC, abstractmethod
from app.models.schemas import FeatureMessage, PredictionResult

class BasePredictor(ABC):
    """
    Tüm Makine Öğrenmesi modelleri için temel (abstract) sınıf.
    SOLID prensiplerinden Liskov Substitution Principle (LSP)'yi sağlamak için
    tüm modeller bu interface'i implement etmek zorundadır.
    """

    @abstractmethod
    def predict(self, features: FeatureMessage) -> PredictionResult:
        """
        Verilen özellikleri (features) alır ve model üzerinden geçirerek
        bir tahmin sonucu (PredictionResult) döndürür.
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """
        Yüklü modelin adı, versiyonu veya durum bilgisi gibi 
        metadata'ları içeren bir sözlük döndürür.
        """
        pass
