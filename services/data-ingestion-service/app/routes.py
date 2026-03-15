# ──────────────────────────────────────────────────────────────
# routes.py — API Endpoint Tanımları (SRP — İnce Kontrolcü)
# ──────────────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   Bu dosyanın TEK sorumluluğu: HTTP isteklerini almak ve
#   iş mantığına yönlendirmek.
#
#   "İnce Kontrolcü" (Thin Controller) Pattern:
#   Route fonksiyonları kısa olmalı. İş mantığını KENDİ İÇİNDE
#   yapmak yerine, IngestionService'e DELEGe eder (yönlendirir).
#
#   ✗ YANLIŞ (Şişman kontrolcü):
#     @router.post("/ingest")
#     async def ingest():
#         csv = pd.read_csv(...)      # İş mantığı route'ta!
#         for row in csv:
#             rabbitmq.publish(row)   # Broker bağımlılığı route'ta!
#
#   ✓ DOĞRU (İnce kontrolcü):
#     @router.post("/ingest")
#     async def ingest(service = Depends(get_ingestion_service)):
#         return await service.ingest_single(asset_id)  # Delege et
#
# GÜVENLİK:
#   - Hata yanıtlarında dahili detaylar GÖSTERİLMEZ
#   - WindSentinelError.detail sadece LOGLARA yazılır
#   - Kullanıcıya sadece .message döndürülür
# ──────────────────────────────────────────────────────────────

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from app.config import settings
from app.schemas import IngestRequest, IngestResponse, HealthResponse, StatusResponse
from app.dependencies import get_ingestion_service, get_rabbitmq_client
from app.ingestion_service import IngestionService
from app.exceptions import (
    WindSentinelError,
    IngestionAlreadyRunningError,
    InvalidAssetIdError,
    DataSourceNotFoundError,
)

logger = logging.getLogger(__name__)

# APIRouter: Route'ları gruplamak için kullanılır
# main.py'de app.include_router(router) ile eklenir
router = APIRouter()


# ──────────────────────────────────────────────────────
# GET /health — Sağlık Kontrolü
# ──────────────────────────────────────────────────────
@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Sistem"],
    summary="Servis sağlık kontrolü",
)
async def health_check():
    """
    Servisin çalışıp çalışmadığını kontrol et.

    Docker healthcheck ve yük dengeleyiciler bu endpoint'i kullanır.
    Her 10 saniyede bir otomatik olarak çağrılır.
    """
    client = get_rabbitmq_client()
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        rabbitmq_connected=client.is_connected,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ──────────────────────────────────────────────────────
# GET /status — İşlem Durumu
# ──────────────────────────────────────────────────────
@router.get(
    "/status",
    response_model=StatusResponse,
    tags=["Sistem"],
    summary="İşlem durumu ve istatistikler",
)
async def get_status(
    service: IngestionService = Depends(get_ingestion_service),
):
    """Aktif ingestion işleminin durumunu ve toplam istatistikleri döner."""
    client = get_rabbitmq_client()
    stats = service.stats
    return StatusResponse(
        total_messages_sent=stats["total_messages_sent"],
        total_files_processed=stats["total_files_processed"],
        is_running=stats["is_running"],
        current_file=stats.get("current_file"),
        last_run=stats.get("last_run"),
        rabbitmq_connected=client.is_connected,
    )


# ──────────────────────────────────────────────────────
# GET /datasets — Kullanılabilir Veri Dosyaları
# ──────────────────────────────────────────────────────
@router.get(
    "/datasets",
    tags=["Veri"],
    summary="SCADA CSV dosyalarını listele",
)
async def list_datasets(
    service: IngestionService = Depends(get_ingestion_service),
):
    """data/raw/Wind Farm A/datasets/ dizinindeki CSV dosyalarını döner."""
    files = service.list_datasets()
    return {"count": len(files), "datasets": files}


# ──────────────────────────────────────────────────────
# POST /ingest — Tek Türbin Veri Alımı
# ──────────────────────────────────────────────────────
@router.post(
    "/ingest",
    response_model=IngestResponse,
    tags=["Veri Alımı"],
    summary="Belirtilen türbin CSV'sini RabbitMQ'ya gönder",
)
async def ingest_turbine(
    request: IngestRequest,
    service: IngestionService = Depends(get_ingestion_service),
):
    """
    Belirtilen asset_id'ye ait CSV dosyasını okuyup
    RabbitMQ measurement.raw kuyruğuna publish eder.

    Güvenlik kontrolleri otomatik yapılır:
    - asset_id whitelist kontrolü
    - Path traversal koruması
    - Pydantic tip doğrulaması
    """
    try:
        result = await service.ingest_single(request.asset_id)
        return IngestResponse(**result)

    except IngestionAlreadyRunningError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except InvalidAssetIdError as e:
        # GÜVENLİK: Dahili detay (e.detail) loglanır ama kullanıcıya GÖNDERİLMEZ
        logger.warning(f"Güvenlik olayı: {e.detail}")
        raise HTTPException(status_code=400, detail=e.message)
    except DataSourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except WindSentinelError as e:
        logger.error(f"Servis hatası: {e.detail}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        # Beklenmeyen hatalarda dahili bilgiyi ASLA sızdırma
        logger.exception("Beklenmeyen hata oluştu")
        raise HTTPException(
            status_code=500,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
        )


# ──────────────────────────────────────────────────────
# POST /ingest/all — Toplu Veri Alımı (Arka Plan)
# ──────────────────────────────────────────────────────
@router.post(
    "/ingest/all",
    tags=["Veri Alımı"],
    summary="Tüm CSV dosyalarını arka planda işle",
)
async def ingest_all(
    background_tasks: BackgroundTasks,
    service: IngestionService = Depends(get_ingestion_service),
):
    """
    Tüm CSV dosyalarını arka plan görevi olarak başlatır.
    İstek hemen döner, işlem arka planda devam eder.
    GET /status ile ilerleme takip edilebilir.
    """
    try:
        if service.is_running:
            raise IngestionAlreadyRunningError(
                message="Zaten bir işlem çalışıyor!",
            )

        client = get_rabbitmq_client()
        if not client.is_connected:
            raise HTTPException(
                status_code=503,
                detail="RabbitMQ bağlantısı yok.",
            )

        background_tasks.add_task(service.ingest_all)

        return {
            "status": "started",
            "message": "Toplu işlem arka planda başlatıldı. GET /status ile takip edin.",
        }

    except IngestionAlreadyRunningError as e:
        raise HTTPException(status_code=409, detail=e.message)
