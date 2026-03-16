# Python 3.11 tabanlı hafif bir image kullan
FROM python:3.11-slim

# Güvenlik (OWASP): Root yetkileriyle çalışmayı engelleyen ve bağımlılıkları yükleyen adım
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Çalışma dizinini oluştur ve ayarla
WORKDIR /app

# Sistem bağımlılıklarını kur (Eğer ileride model için gcc v.b. gerekirse diye)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Gereksinimleri kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje kodlarını kopyala
COPY . .

# Klasör yetkilerini appuser kullanıcısına devret
RUN chown -R appuser:appuser /app

# appuser'a geç
USER appuser

# Portu dışarı aç (İsteğe bağlı, Docker-compose yönetecek)
EXPOSE 8000

# Servisi başlat
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
