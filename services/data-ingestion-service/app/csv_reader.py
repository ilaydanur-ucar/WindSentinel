# ──────────────────────────────────────────────────────────────
# csv_reader.py — SCADA CSV Okuyucu (DIP + SRP)
# ──────────────────────────────────────────────────────────────
#
# OPTİMİZASYON:
#   pandas (~150MB) yerine Python'un built-in csv modülünü kullanıyoruz.
#   - Sıfır ekstra bağımlılık (daha küçük Docker image)
#   - Daha hızlı Docker build süresi
#   - csv modülü chunk chunk okuma için zaten ideal
#
# DIP UYGULAMASI:
#   Bu sınıf IDataReader interface'ini implemente eder.
#
# SRP UYGULAMASI:
#   TEK sorumluluk: CSV dosyalarını oku ve mesaj formatına dönüştür.
# ──────────────────────────────────────────────────────────────

import csv
import logging
from pathlib import Path
from typing import Generator

from app.config import settings
from app.exceptions import DataSourceNotFoundError, DataReadError
from app.schemas import MeasurementMessage

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────
# CSV Kolon Eşlemesi (DRY — tek yerde tanımlı)
# ──────────────────────────────────────────────────────
COLUMN_MAPPING: dict[str, str] = {
    "time_stamp": "timestamp",
    "asset_id": "asset_id",
    "status_type_id": "status_type_id",
    "wind_speed_3_avg": "wind_speed",
    "power_30_avg": "power_output",
    "sensor_18_avg": "generator_rpm",
    "sensor_52_avg": "rotor_rpm",
    "sensor_12_avg": "gearbox_oil_temp",
    "sensor_50_avg": "total_active_power",
    "reactive_power_28_avg": "reactive_power_inductive",
    "reactive_power_27_avg": "reactive_power_capacitive",
}

_REQUIRED_CSV_COLUMNS: set[str] = set(COLUMN_MAPPING.keys())


class ScadaCsvReader:
    """
    IDataReader interface'inin SCADA CSV implementasyonu.

    Built-in csv modülü ile hafif ve hızlı okuma.
    """

    def __init__(self, data_path: str = None):
        self._data_path = Path(data_path or settings.SCADA_DATA_PATH)
        self._datasets_dir = self._data_path / "raw" / "Wind Farm A" / "datasets"

    def list_sources(self) -> list[dict]:
        """Kullanılabilir comma_*.csv dosyalarını listele."""
        if not self._datasets_dir.exists():
            logger.warning(f"⚠️ Veri dizini bulunamadı: {self._datasets_dir}")
            return []

        csv_files = []
        for f in sorted(self._datasets_dir.glob("comma_*.csv")):
            try:
                asset_id = int(f.stem.replace("comma_", ""))
                csv_files.append({
                    "asset_id": asset_id,
                    "filename": f.name,
                    "path": str(f),
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
                })
            except ValueError:
                continue

        logger.info(f"📂 {len(csv_files)} CSV dosyası bulundu")
        return csv_files

    def read_chunks(
        self,
        source_path: str,
        chunk_size: int = None,
    ) -> Generator[list[dict], None, None]:
        """
        CSV'yi chunk halinde oku (built-in csv modülü ile).

        pandas yerine csv.DictReader kullanıyoruz:
        - Sıfır bağımlılık (Python ile birlikte gelir)
        - Satır satır okur → bellek dostu
        - chunk_size kadar satırı biriktirip yield eder

        Args:
            source_path: CSV dosyasının yolu
            chunk_size: Her chunk'taki satır sayısı

        Yields:
            [dict, dict, ...] → Her dict bir MeasurementMessage
        """
        if chunk_size is None:
            chunk_size = settings.CHUNK_SIZE

        file_path = Path(source_path)
        if not file_path.exists():
            raise DataSourceNotFoundError(
                message="Veri dosyası bulunamadı.",
                detail=f"Dosya mevcut değil: {source_path}",
            )

        logger.info(f"📖 CSV okunuyor: {file_path.name} (chunk_size={chunk_size})")

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                chunk: list[dict] = []
                chunk_num = 0

                for row in reader:
                    message = self._row_to_message(row)
                    if message is not None:
                        chunk.append(message)

                    # chunk_size'a ulaşınca yield et
                    if len(chunk) >= chunk_size:
                        chunk_num += 1
                        logger.info(f"  📦 Chunk {chunk_num}: {len(chunk)} mesaj hazır")
                        yield chunk
                        chunk = []

                # Son kalan satırları da gönder
                if chunk:
                    chunk_num += 1
                    logger.info(f"  📦 Chunk {chunk_num}: {len(chunk)} mesaj hazır (son)")
                    yield chunk

        except DataSourceNotFoundError:
            raise
        except Exception as e:
            raise DataReadError(
                message="Veri dosyası okunurken hata oluştu.",
                detail=f"CSV okuma hatası ({file_path.name}): {e}",
            )

    def _row_to_message(self, row: dict) -> dict | None:
        """
        Tek bir CSV satırını (dict) mesaj formatına dönüştür.

        csv.DictReader her satırı {"kolon_adı": "değer"} olarak verir.
        Biz bunu MeasurementMessage formatına çeviriyoruz.

        Güvenlik: Pydantic ile validation yapılır.
        """
        try:
            asset_id = int(row.get("asset_id", -1))

            raw_data = {
                "timestamp": row.get("time_stamp", ""),
                "asset_id": asset_id,
                "turbine_id": _get_turbine_id(asset_id),
                "status_type_id": int(row.get("status_type_id", 0)),
                "wind_speed": _safe_float(row.get("wind_speed_3_avg")),
                "power_output": _safe_float(row.get("power_30_avg")),
                "generator_rpm": _safe_float(row.get("sensor_18_avg")),
                "total_active_power": _safe_float(row.get("sensor_50_avg")),
                "reactive_power_inductive": _safe_float(row.get("reactive_power_28_avg")),
                "reactive_power_capacitive": _safe_float(row.get("reactive_power_27_avg")),
                "rotor_rpm": _safe_float(row.get("sensor_52_avg")),
                "gearbox_oil_temp": _safe_float(row.get("sensor_12_avg")),
            }

            validated = MeasurementMessage(**raw_data)
            return validated.model_dump()

        except Exception as e:
            logger.debug(f"⚠️ Satır dönüştürme hatası (atlandı): {e}")
            return None


# ──────────────────────────────────────────────────────
# Yardımcı Fonksiyonlar (DRY)
# ──────────────────────────────────────────────────────

def _get_turbine_id(asset_id: int) -> str:
    """asset_id → türbin kodu (ör: 0 → 'WFA-T00')."""
    return f"WFA-T{str(asset_id).zfill(2)}"


def _safe_float(value) -> float:
    """Değeri güvenli şekilde float'a çevir. Geçersiz → 0.0"""
    try:
        result = float(value)
        if result != result:  # NaN kontrolü
            return 0.0
        return round(result, 6)
    except (ValueError, TypeError):
        return 0.0
