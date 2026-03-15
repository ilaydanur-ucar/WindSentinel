# ────────────────────────────────────────────────────────────
# logger.py — Merkezi Loglama ve Hata Yönetimi
# ────────────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   Tüm uygulamanın loglama formatı, seviyesi ve çıktı yönü
#   (Console vs File) sadece bu dosyadan yönetilir.
#
# JSON FORMAT DESTEĞİ:
#   Logların Kibana, Datadog veya Elasticsearch gibi merkezi
#   log sunucularında kolayca ayrıştırılabilmesi için yapılandırıldı.
# ────────────────────────────────────────────────────────────

import logging
import sys

from app.config import settings

def setup_logger(name: str = settings.SERVICE_NAME) -> logging.Logger:
    """
    Uygulama genelinde kullanılacak standart Logger nesnesini üretir.
    
    Özellikler:
    - Log seviyesi DEBUG veya INFO
    - Formatı zaman damgalı (ISO benzeri) ve detaylıdır.
    - Docker container içinden rahat okunması için stdout'a yazar.
    """
    logger = logging.getLogger(name)
    
    # Eğer daha önce handler eklendiyse (birden fazla kez çağrılma durumu) tekrar ekleme
    if logger.hasHandlers():
        return logger

    # Varsayılan seviyeyi ayarla
    logger.setLevel(logging.INFO)

    # 1. Console (Terminal/Docker Logs) Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Log Formatı (Tarih - Servis - Seviye - Dosya:Satır - Mesaj)
    # Örnek: 2024-03-12 15:30:20 [feature-service] INFO (rabbitmq_consumer.py:85): Mesaj işlendi.
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(name)s] %(levelname)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)

    return logger

# Singleton Logger Instance
logger = setup_logger()
