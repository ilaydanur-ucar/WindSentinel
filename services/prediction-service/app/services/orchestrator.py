import asyncio
import json
from pydantic import ValidationError
from typing import Optional

from app.infrastructure.rabbitmq_client import RabbitMQClient
from app.ml.base import BasePredictor
from app.models.schemas import FeatureMessage, PredictionResult
from app.core.config import settings

class PredictionOrchestrator:
    """
    Sistemin ana kontrolcüsü (Coordinator / Orchestrator).
    SOLID SRP (Single Responsibility Principle) gereği: 
    Kendi içinde rabbitmq baglantısı açmaz veya ML Modeli tutmaz; Bunlar 'Dependecy Injection' ile içeri verilir.
    
    Tek amacı: Gelen datayı al-> Model'e ver -> Sonucu kontrol et -> Publish edilecekse Publish et.
    """
    def __init__(self, rabbitmq_client: RabbitMQClient, predictor: BasePredictor):
        self.rabbitmq_client = rabbitmq_client
        self.predictor = predictor

    async def _process_single_message(self, payload: dict) -> None:
        """
        Consumer tarafından çağrılan Callback fonksiyonu.
        """
        try:
            # 1. Gelen veriyi Pydantic ile Validate Et (Guvenlik: extra="forbid")
            feature_msg = FeatureMessage(**payload)
            
            # 2. İş mantığını (ML Model Prediction) çağır
            prediction_result: PredictionResult = self.predictor.predict(feature_msg)
            
            # 3. Yalnızca ANOMALİ (Arıza Şüphesi) Varsa Publish Et
            if prediction_result.is_anomaly:
                # PredictionResult modelimizi dict'e çevirirken timestamp gibi tarihlerin 
                # serialization'ını pydantic model_dump ile kolayca hallederiz
                data_to_publish = json.loads(prediction_result.model_dump_json())
                
                await self.rabbitmq_client.publish_message(
                    settings.RABBITMQ_PUBLISH_QUEUE, 
                    data_to_publish
                )
                print(f"ANOMALY DETECTED and published to {settings.RABBITMQ_PUBLISH_QUEUE}: {data_to_publish}")

        except ValidationError as ve:
            print(f"Validation Error (Invalid Payload from Queue): {ve}")
        except Exception as e:
            print(f"Orchestrator unexpected error: {e}")

    async def start_listening(self):
        """
        Arka planda (Background Task) asenkron olarak RabbitMQ dinlemeye başla
        """
        print(f"PredictionOrchestrator started listening on {settings.RABBITMQ_CONSUME_QUEUE}...")
        await self.rabbitmq_client.consume_messages(
            settings.RABBITMQ_CONSUME_QUEUE, 
            self._process_single_message
        )
