# 1. Base Image (Alpine veya Slim tercih edilmeli)
FROM python:3.11-slim

# OS seviyesinde güncellemeler (Vulnerability yamaları)
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# 2. Çalışma Dizini
WORKDIR /app

# 3. GÜVENLİK (OWASP A05) - Non-root AppUser Oluştur
# Root haklarıyla çalışan container'lar, docker escape saldırılarında 
# host makineye kök (root) erişimi verebilir. Bu risk kapatılıyor.
RUN addgroup --system appgroup && \
    adduser --system --group --no-create-home appuser

# 4. Bağımlılıkları Sabit Versiyonlarla (Pinned) Yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Kaynak Kodları Kopyala
COPY . .

# 6. Yetkilendirme: Tüm /app dizininin sahipliğini kısıtlı kullanıcıya ver
RUN chown -R appuser:appgroup /app

# 7. UYARI: Kullanıcı değiştiriliyor. 
# Bundan sonraki tüm komutlar (CMD dahil) root olmayan 'appuser' ile çalışacak!
USER appuser

# 8. Uygulamayı Başlat
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
