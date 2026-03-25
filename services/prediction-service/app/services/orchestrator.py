import asyncio
import json
import numpy as np
from collections import defaultdict, deque
from pydantic import ValidationError

from app.infrastructure.rabbitmq_client import RabbitMQClient
from app.ml.base import BasePredictor
from app.models.schemas import FeatureMessage, PredictionResult
from app.core.config import settings
from app.core.feature_columns import ROLLING_WINDOW


class PredictionOrchestrator:
    """
    Gelen feature verisini alir, time-series feature'lari hesaplar,
    ML modeline verir ve anomali varsa publish eder.
    """

    def __init__(self, rabbitmq_client: RabbitMQClient, predictor: BasePredictor):
        self.rabbitmq_client = rabbitmq_client
        self.predictor = predictor
        # Her turbin icin ayri rolling window buffer (data leakage onlemi)
        self._buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=ROLLING_WINDOW))
        # Turbin bazli power curve profili (wind_speed_bin -> ortalama power)
        # Daha buyuk pencere: turbin davranisini ogrenme icin
        self._power_profiles: dict[str, deque] = defaultdict(lambda: deque(maxlen=500))

    def _compute_time_series_features(self, feature_msg: FeatureMessage) -> dict:
        """
        Rolling mean, std, delta ve deviation hesapla.
        Her turbin icin ayri buffer tutar (cross-turbine leakage yok).
        """
        turbine_id = feature_msg.turbine_id
        buf = self._buffers[turbine_id]

        current = {
            'power_output': feature_msg.power_output,
            'generator_rpm': feature_msg.generator_rpm,
            'wind_speed': feature_msg.wind_speed,
        }
        buf.append(current)

        # Buffer'dan numpy array'ler olustur
        ts_features = {}
        for col in ['power_output', 'generator_rpm', 'wind_speed']:
            values = [b[col] for b in buf]
            arr = np.array(values, dtype=np.float64)

            ts_features[f'{col}_rolling_mean'] = float(np.mean(arr))
            ts_features[f'{col}_rolling_std'] = float(np.std(arr)) if len(arr) > 1 else 0.0

            # Delta: son iki olcum arasindaki fark
            if len(arr) >= 2:
                ts_features[f'{col}_delta'] = float(arr[-1] - arr[-2])
            else:
                ts_features[f'{col}_delta'] = 0.0

        # Power deviation: mevcut guc - rolling ortalama
        ts_features['power_deviation'] = current['power_output'] - ts_features['power_output_rolling_mean']

        # Power curve deviation: turbin bazli ruzgar-guc profilinden sapma
        # Her turbin kendi "normal" guc egrisini ogrenir
        profile = self._power_profiles[turbine_id]
        profile.append((feature_msg.wind_speed, feature_msg.power_output))

        if len(profile) >= 10:
            ws = feature_msg.wind_speed
            # Benzer ruzgar hizindaki (+-1 m/s) ortalama gucu bul
            similar = [p for w, p in profile if abs(w - ws) <= 1.0]
            if len(similar) >= 3:
                expected_power = float(np.mean(similar))
                ts_features['power_curve_deviation'] = feature_msg.power_output - expected_power
            else:
                ts_features['power_curve_deviation'] = 0.0
        else:
            ts_features['power_curve_deviation'] = 0.0

        return ts_features

    async def _process_single_message(self, payload: dict) -> None:
        try:
            feature_msg = FeatureMessage(**payload)

            # Time-series feature'lari hesapla
            ts_features = self._compute_time_series_features(feature_msg)

            # Base + time-series feature'lari birlestir
            enriched_payload = {**payload, **ts_features}

            prediction_result: PredictionResult = self.predictor.predict_with_ts(
                feature_msg, ts_features
            )

            if prediction_result.is_anomaly:
                data_to_publish = json.loads(prediction_result.model_dump_json())
                await self.rabbitmq_client.publish_message(
                    settings.RABBITMQ_PUBLISH_QUEUE,
                    data_to_publish
                )
                print(f"ANOMALY DETECTED: {prediction_result.turbine_id} "
                      f"score={prediction_result.confidence:.4f} "
                      f"severity={prediction_result.severity}")

        except ValidationError as ve:
            print(f"Validation Error: {ve}")
        except Exception as e:
            print(f"Orchestrator error: {e}")

    async def start_listening(self):
        print(f"PredictionOrchestrator started listening on {settings.RABBITMQ_CONSUME_QUEUE}...")
        await self.rabbitmq_client.consume_messages(
            settings.RABBITMQ_CONSUME_QUEUE,
            self._process_single_message
        )
