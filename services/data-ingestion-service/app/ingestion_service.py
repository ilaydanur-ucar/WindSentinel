# ──────────────────────────────────────────────────────────────
# ingestion_service.py — İş Mantığı Orchestrator (SRP + DIP)
# ──────────────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   Bu dosyanın TEK sorumluluğu: Veri alım iş mantığını yönetmek.
#   - CSV OKUMA → csv_reader.py'nin işi
#   - RABBITMQ → rabbitmq_client.py'nin işi
#   - HTTP API → routes.py'nin işi
#   - GÜVENLİK → security.py'nin işi
#   Bu dosya sadece bunları BİRLEŞTİRİR (orchestration).
#
# DIP UYGULAMASI:
#   Bu sınıf somut sınıflara (RabbitMQClient, ScadaCsvReader)
#   DEĞİL, soyut interface'lere (IMessageBroker, IDataReader)
#   bağımlıdır. Constructor'da interface tipinde parametre alır.
#
#   class IngestionService:
#       def __init__(self, broker: IMessageBroker, reader: IDataReader):
#                           ↑                        ↑
#                    abstract interface        abstract interface
#
#   Bu sayede test yazarken mock nesneler enjekte edebiliriz.
# ──────────────────────────────────────────────────────────────

import logging
from datetime import datetime, timezone

from app.interfaces import IMessageBroker, IDataReader
from app.security import validate_asset_id, build_safe_csv_path
from app.exceptions import (
    IngestionAlreadyRunningError,
    DataSourceNotFoundError,
)

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Veri alım sürecini yöneten ana iş mantığı sınıfı.

    Bu sınıf CSV okuma ve RabbitMQ gönderme işlemlerini
    koordine eder (orchestration pattern).

    DIP: Somut sınıflar yerine interface'lere bağımlıdır.
    Test yazarken mock broker ve mock reader enjekte edilebilir.
    """

    def __init__(self, broker: IMessageBroker, reader: IDataReader):
        """
        Dependency Injection ile bağımlılıkları al.

        Args:
            broker: Mesaj kuyruğu sistemi (RabbitMQ, Kafka vb.)
            reader: Veri okuyucu (CSV, API vb.)
        """
        self._broker = broker
        self._reader = reader

        # İşlem durumu (state)
        self._stats = {
            "total_messages_sent": 0,
            "total_files_processed": 0,
            "is_running": False,
            "current_file": None,
            "last_run": None,
        }

    @property
    def stats(self) -> dict:
        """İşlem istatistiklerinin kopyasını döndür (encapsulation)."""
        return self._stats.copy()

    @property
    def is_running(self) -> bool:
        """Bir ingestion işleminin çalışıp çalışmadığı."""
        return self._stats["is_running"]

    async def ingest_single(self, asset_id: int) -> dict:
        """
        Tek bir türbin CSV'sini oku ve RabbitMQ'ya publish et.

        İş Akışı:
            1. asset_id güvenlik kontrolü (whitelist)
            2. Güvenli dosya yolu oluştur (path traversal koruması)
            3. CSV'yi chunk chunk oku
            4. Her chunk'ı RabbitMQ'ya gönder
            5. İstatistikleri güncelle

        Args:
            asset_id: İşlenecek türbin ID'si

        Returns:
            {"status": "completed", "messages_sent": 1234, ...}

        Raises:
            IngestionAlreadyRunningError: Zaten bir işlem çalışıyor
            InvalidAssetIdError: Geçersiz asset_id
            DataSourceNotFoundError: CSV bulunamadı
        """
        # 1. Çalışan işlem kontrolü
        if self._stats["is_running"]:
            raise IngestionAlreadyRunningError(
                message=f"Zaten bir işlem çalışıyor: {self._stats['current_file']}",
            )

        # 2. Güvenlik: asset_id whitelist kontrolü
        validate_asset_id(asset_id)

        # 3. Güvenlik: Güvenli dosya yolu oluştur
        safe_path = build_safe_csv_path(asset_id)
        if not safe_path.exists():
            raise DataSourceNotFoundError(
                message=f"asset_id={asset_id} için veri dosyası bulunamadı.",
                detail=f"Dosya mevcut değil: {safe_path}",
            )

        # 4. İşlemi başlat
        filename = safe_path.name
        logger.info(f"🔄 Ingestion başlatılıyor: {filename}")
        self._stats["is_running"] = True
        self._stats["current_file"] = filename

        messages_sent = 0

        try:
            # 5. CSV'yi oku ve RabbitMQ'ya gönder
            for chunk_messages in self._reader.read_chunks(str(safe_path)):
                for message in chunk_messages:
                    if await self._broker.publish(message):
                        messages_sent += 1

            # 6. İstatistikleri güncelle
            self._stats["total_messages_sent"] += messages_sent
            self._stats["total_files_processed"] += 1
            self._stats["last_run"] = datetime.now(timezone.utc).isoformat()

            logger.info(
                f"✅ Ingestion tamamlandı: {filename} → {messages_sent} mesaj"
            )

            return {
                "status": "completed",
                "asset_id": asset_id,
                "messages_sent": messages_sent,
                "message": f"{filename}: {messages_sent} mesaj RabbitMQ'ya gönderildi.",
            }

        finally:
            # Her durumda (başarı/hata) is_running'i kapat
            self._stats["is_running"] = False
            self._stats["current_file"] = None

    async def ingest_all(self) -> None:
        """
        Tüm CSV dosyalarını sırayla işle.

        Bu metot arka plan görevi olarak çalıştırılmak üzere
        tasarlanmıştır (routes.py'den BackgroundTasks ile çağrılır).
        """
        if self._stats["is_running"]:
            raise IngestionAlreadyRunningError(
                message="Zaten bir işlem çalışıyor!",
            )

        csv_files = self._reader.list_sources()
        self._stats["is_running"] = True

        logger.info(f"🔄 Toplu ingestion: {len(csv_files)} dosya")

        for file_info in csv_files:
            self._stats["current_file"] = file_info["filename"]
            messages_sent = 0

            try:
                for chunk in self._reader.read_chunks(file_info["path"]):
                    for message in chunk:
                        if await self._broker.publish(message):
                            messages_sent += 1

                self._stats["total_messages_sent"] += messages_sent
                self._stats["total_files_processed"] += 1
                logger.info(f"  ✅ {file_info['filename']}: {messages_sent} mesaj")

            except Exception as e:
                logger.error(f"  ❌ {file_info['filename']}: {e}")

        self._stats["is_running"] = False
        self._stats["current_file"] = None
        self._stats["last_run"] = datetime.now(timezone.utc).isoformat()
        logger.info("✅ Toplu ingestion tamamlandı!")

    def list_datasets(self) -> list[dict]:
        """Kullanılabilir veri kaynaklarını listele."""
        return self._reader.list_sources()
