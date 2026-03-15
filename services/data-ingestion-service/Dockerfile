# ────────────────────────────────────────────
# Data Ingestion Service - Dockerfile
# ────────────────────────────────────────────
# Bu dosya, servisin Docker container olarak
# çalışması için gerekli "tarif"tir.
#
# Katmanlı Build:
#   Docker her adımı (RUN, COPY) ayrı bir "layer" olarak saklar.
#   requirements.txt ayrı kopyalanır çünkü:
#   → Kod değişse bile bağımlılıklar cache'den gelir (hızlı rebuild)
# ────────────────────────────────────────────

# 1. Python 3.11 slim (küçük boyutlu) base image
FROM python:3.11-slim

# 2. Çalışma dizini
WORKDIR /app

# 3. Bağımlılıkları önce kopyala ve yükle (Docker cache optimizasyonu)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Uygulama kodunu kopyala
COPY app/ ./app/

# 5. Container başladığında çalışacak komut
#    app.main:app → app paketindeki main.py'deki app nesnesi
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
