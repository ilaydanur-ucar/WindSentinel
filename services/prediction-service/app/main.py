import os
import uvicorn
import asyncio
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager

from app.core.config import settings
from app.infrastructure.rabbitmq_client import RabbitMQClient
from app.ml.dummy_predictor import DummyPredictor
from app.services.orchestrator import PredictionOrchestrator

# Dependency'lerin Instance'larını hazırlayalım
# İleride DummyPredictor yerine XGBoostPredictor eklendiğinde sadece buradaki satir değişecek (OCP)
predictor_instance = DummyPredictor()
rabbitmq_client_instance = RabbitMQClient()
orchestrator = PredictionOrchestrator(
    rabbitmq_client=rabbitmq_client_instance,
    predictor=predictor_instance
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    print("Starting up Prediction Service...")
    # 1. RabbitMQ Bağlan
    await rabbitmq_client_instance.connect()
    
    # 2. Arka plan dinleme loopunu başlat 
    # (Fastapi ana threadi bloklamamak için asyncio.create_task kullanıyoruz)
    consume_task = asyncio.create_task(orchestrator.start_listening())
    
    yield # Uygulamanın çalışır kaldığı süre
    
    # SHUTDOWN
    print("Shutting down Prediction Service...")
    consume_task.cancel()
    await rabbitmq_client_instance.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """
    Docker Healthcheck ve Orchestrator sağlığı için Endpoint.
    Servis ayakta mı? Bağımlılıklar yüklendi mi?
    """
    mq_connected = rabbitmq_client_instance.connection is not None and not rabbitmq_client_instance.connection.is_closed
    model_loaded = True if predictor_instance else False
    
    status = "ok" if mq_connected and model_loaded else "degraded"
    
    return {
        "status": status,
        "model_loaded": model_loaded,
        "rabbitmq": "connected" if mq_connected else "disconnected"
    }

@app.get("/model/info")
async def model_info():
    """
    O an aktif olan (hafızaya yüklenmiş) ML Modeli bilgilerini döndür.
    """
    if predictor_instance:
        return predictor_instance.get_model_info()
    return {"status": "error", "message": "No model loaded"}

# Manuel run: uvicorn app.main:app --host 0.0.0.0 --port 8000
