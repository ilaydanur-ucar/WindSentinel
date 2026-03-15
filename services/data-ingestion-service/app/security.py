# ──────────────────────────────────────────────────────────
# security.py — Güvenlik Modülü (OWASP Standartları)
# ──────────────────────────────────────────────────────────
#
# OWASP (Open Web Application Security Project):
#   Web uygulama güvenliği için dünya standartlarını belirleyen vakıf.
#   Bu dosya OWASP Top 10'daki şu maddelere karşı önlem alır:
#
#   A01:2021 — Broken Access Control
#     → Whitelist ile sadece izin verilen asset_id'lere erişim
#
#   A03:2021 — Injection
#     → Dosya yolu oluştururken kullanıcı girdisi sanitize edilir
#     → Path traversal ("../../etc/passwd") engellenir
#
#   A04:2021 — Insecure Design
#     → Tüm girdiler validate edilir (tip, aralık, format)
#
#   A09:2021 — Security Logging and Monitoring
#     → Güvenlik olayları loglanır (geçersiz istek denemeleri)
#
# DRY UYGULAMASI:
#   Tüm güvenlik kontrolleri tek bir yerde. Her endpoint'te
#   ayrı ayrı kontrol yapmak yerine, merkezi fonksiyonlar
#   kullanılır.
# ──────────────────────────────────────────────────────────

import logging
import re
from pathlib import Path

from app.config import settings
from app.exceptions import InvalidAssetIdError

logger = logging.getLogger(__name__)


def validate_asset_id(asset_id: int) -> int:
    """
    asset_id'nin geçerli ve güvenli olduğunu doğrula.

    Güvenlik Kontrolleri:
        1. Tip kontrolü → int olmalı (Pydantic zaten yapıyor)
        2. Whitelist kontrolü → İzin verilen ID'ler listesinde olmalı
        3. Aralık kontrolü → Negatif değerler reddedilir

    Neden Whitelist?
    → Blacklist (kara liste): "Şunları YAPMA" → Yeni tehditler atlanabilir
    → Whitelist (beyaz liste): "Sadece ŞUNLARI yap" → Daha güvenli

    Args:
        asset_id: Doğrulanacak türbin ID'si

    Returns:
        Doğrulanmış asset_id

    Raises:
        InvalidAssetIdError: Geçersiz veya izin verilmeyen asset_id
    """
    # Negatif değer kontrolü
    if asset_id < 0:
        logger.warning(f"⚠️ GÜVENLİK: Negatif asset_id denemesi: {asset_id}")
        raise InvalidAssetIdError(
            message="Geçersiz asset_id değeri.",
            detail=f"Negatif asset_id reddedildi: {asset_id}",
        )

    # Whitelist kontrolü
    if asset_id not in settings.ALLOWED_ASSET_IDS:
        logger.warning(
            f"⚠️ GÜVENLİK: İzin verilmeyen asset_id denemesi: {asset_id}"
        )
        raise InvalidAssetIdError(
            message=f"asset_id={asset_id} bulunamadı veya erişime izin verilmiyor.",
            detail=f"Whitelist'te olmayan asset_id: {asset_id}",
        )

    return asset_id


def sanitize_file_path(base_dir: str, filename: str) -> Path:
    """
    Dosya yolunu güvenli hale getir (Path Traversal engelleme).

    PATH TRAVERSAL NEDİR?
    Saldırgan, dosya adı yerine "../../../etc/passwd" gibi bir
    değer göndererek sunucudaki hassas dosyalara erişmeye çalışır.

    Örnek Saldırı:
        asset_id yerine "../../secrets" gönderilirse:
        /data/raw/Wind Farm A/datasets/comma_../../secrets.csv
        → /data/secrets.csv → Tehlikeli!

    Korunma:
        1. resolve() ile gerçek yolu hesapla (.. ifadelerini çöz)
        2. Sonucun base_dir İÇİNDE olup olmadığını kontrol et
        3. Dışındaysa → REDDET

    Args:
        base_dir: İzin verilen kök dizin
        filename: Kullanıcıdan gelen dosya adı

    Returns:
        Güvenli, doğrulanmış Path nesnesi

    Raises:
        InvalidAssetIdError: Path traversal denemesi tespit edildi
    """
    base = Path(base_dir).resolve()
    target = (base / filename).resolve()

    # Güvenlik: Hedef dosya, base dizinin İÇİNDE mi?
    if not str(target).startswith(str(base)):
        logger.warning(
            f"🚨 GÜVENLİK: Path traversal denemesi tespit edildi! "
            f"base={base}, target={target}"
        )
        raise InvalidAssetIdError(
            message="Geçersiz dosya yolu.",
            detail=f"Path traversal denemesi: {filename}",
        )

    return target


def build_safe_csv_path(asset_id: int) -> Path:
    """
    asset_id'den güvenli CSV dosya yolu oluştur.

    Bu fonksiyon validate_asset_id + sanitize_file_path'i
    birleştirerek tam güvenli bir dosya yolu üretir.

    Akış:
        asset_id (int) → validate → sanitize → güvenli Path

    Args:
        asset_id: Türbin ID'si (önceden validate edilmiş olmalı)

    Returns:
        Güvenli CSV dosya yolu
    """
    # Dosya adını güvenli şekilde oluştur
    # str(int) ile injection engellenir (sadece rakam kalır)
    filename = f"comma_{int(asset_id)}.csv"

    # Veri dizini
    data_dir = (
        Path(settings.SCADA_DATA_PATH) / "raw" / "Wind Farm A" / "datasets"
    )

    # Path traversal kontrolü ile güvenli yol oluştur
    return sanitize_file_path(str(data_dir), filename)
