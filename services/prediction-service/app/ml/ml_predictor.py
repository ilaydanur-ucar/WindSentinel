import os
import joblib
import json
import numpy as np
import logging
import xgboost as xgb
import time
from typing import Dict, Any

from app.ml.base import BasePredictor
from app.models.schemas import FeatureMessage, PredictionResult
from app.core.feature_columns import FEATURE_COLUMNS, ANOMALY_THRESHOLD
from app.core.security import verify_file_checksum

logger = logging.getLogger(__name__)

class MLPredictor(BasePredictor):
    """
    Gerçek Makine Öğrenmesi modellerini (Isolation Forest & XGBoost) yükleyen
     ve ağırlıklı ensemble mantığıyla tahmin yapan sınıf.
    """

    def __init__(self, model_dir: str = "models_data"):
        self.model_dir = model_dir
        self.iso_forest = None
        self.xgb_model = xgb.XGBClassifier() # Initialize empty model for JSON loading
        self.checksums = {}
        
        self._load_models()

    def _load_models(self):
        """Modelleri checksum kontrolü yaparak RAM'e yükler."""
        checksum_path = os.path.join(self.model_dir, "checksums.json")
        iso_path = os.path.join(self.model_dir, "isolation_forest.pkl")
        xgb_path = os.path.join(self.model_dir, "xgboost_model.json")

        if not os.path.exists(checksum_path):
            raise FileNotFoundError(f"Checksum dosyası bulunamadı: {checksum_path}")
        
        with open(checksum_path, "r") as f:
            self.checksums = json.load(f)

        model_files = {
            "isolation_forest.pkl": iso_path,
            "xgboost_model.json": xgb_path
        }

        for filename, path in model_files.items():
            expected = self.checksums.get(filename)
            if not verify_file_checksum(path, expected):
                logger.critical(f"GÜVENLİK İHLALİ: {filename} doğrulaması başarısız!")
                raise RuntimeError(f"Model bütünlüğü bozulmuş: {filename}")

        self.iso_forest = joblib.load(iso_path)
        self.xgb_model.load_model(xgb_path)
        logger.info("ML modelleri başarıyla yüklendi (IsoForest: Pickle, XGBoost: JSON).")

    def _get_iso_normalized(self, X: np.ndarray) -> float:
        raw_score = self.iso_forest.decision_function(X)[0]
        return 1 / (1 + np.exp(raw_score))

    def predict(self, features: FeatureMessage) -> PredictionResult:
        start_time = time.perf_counter()
        try:
            input_vector = np.array([[getattr(features, f) for f in FEATURE_COLUMNS]], dtype=np.float32)

            iso_score = self._get_iso_normalized(input_vector)
            xgb_prob = float(self.xgb_model.predict_proba(input_vector)[0][1])

            final_score = (0.6 * iso_score) + (0.4 * xgb_prob)
            is_anomaly = final_score > ANOMALY_THRESHOLD

            end_time = time.perf_counter()
            inference_ms = (end_time - start_time) * 1000
            
            if inference_ms > 100: # 100ms kritik eşik (Latency)
                logger.warning(f"YÜKSEK GECİKME: Prediction took {inference_ms:.2f}ms")

            return PredictionResult(
                is_anomaly=is_anomaly,
                confidence=round(final_score, 4),
                anomaly_score=round(iso_score, 4),
                fault_type="generic_anomaly" if is_anomaly else "normal"
            )

        except Exception as e:
            logger.error(f"Tahmin sırasında hata oluştu: {e}")
            raise e

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type": "Hybrid (IsolationForest + XGBoost)",
            "features_used": FEATURE_COLUMNS,
            "anomaly_threshold": ANOMALY_THRESHOLD,
            "iso_forest_params": self.iso_forest.get_params() if self.iso_forest else None,
            "xgboost_params": self.xgb_model.get_params() if self.xgb_model else None
        }
