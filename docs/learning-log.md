# WindSentinel — Öğrenme Logu 📝

Bu dosya, projenin geliştirilmesi sırasında yapılan her adımı, kullanılan teknolojileri ve öğrenilen kavramları detaylıca açıklar.

---

## Hafta 1-2: Planlama ve Altyapı (Tamamlandı)

### Ne Yapıldı?
- Proje mimarisi tasarlandı (5 mikroservis)
- Docker Compose ile RabbitMQ ve PostgreSQL ayağa kaldırıldı
- SCADA veri seti analiz edildi, 81 sensör arasından 6 kritik sensör seçildi
- API kontratları ve veritabanı şeması oluşturuldu
- RabbitMQ queue/exchange tanımları yapıldı

---

## Hafta 2: Data Ingestion Service

### 📅 Tarih: 2026-03-14

### 🎯 Hedef
SCADA CSV dosyalarını okuyan ve RabbitMQ'ya mesaj olarak gönderen ilk mikroservisi yazmak.

---

### Kavram 1: Mikroservis Nedir?

**Monolitik (Tek Parça) Mimari:**
```
┌──────────────────────────────────────┐
│           TEK UYGULAMA               │
│  CSV Okuma + ML + API + Bildirim     │
│  Hepsi aynı kodda, aynı uygulamada  │
└──────────────────────────────────────┘
```
Bir yer bozulursa → HER ŞEY DURUR!

**Mikroservis Mimari:**
```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Veri     │  │ Feature  │  │ Tahmin   │  │ Bildirim │
│ Okuyucu  │→ │ Mühendis │→ │ Servisi  │→ │ Servisi  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```
- Her servis BAĞIMSIZ çalışır
- Biri çökerse diğerleri devam eder
- Her birinin kendi Docker container'ı var
- İstersen farklı dillerde yazılabilir (Python, Node.js, Go...)

---

### Kavram 2: RabbitMQ Nedir ve Nasıl Çalışır?

RabbitMQ bir **mesaj kuyruğu** (message broker) sistemidir. Düşün ki bir postane:

```
   Gönderici               Postane              Alıcı
  (Producer)              (RabbitMQ)           (Consumer)
      │                      │                    │
      │   "Mektup gönder"    │                    │
      │─────────────────────>│                    │
      │                      │   "Mektubun var"   │
      │                      │───────────────────>│
      │                      │                    │
```

#### Temel RabbitMQ Kavramları:

**1. Exchange (Dağıtıcı)**
- Mesajların İLK gittiği yer
- Hangi kuyruğa gideceğine karar verir
- Bizim projede: `wind.events` (topic exchange)
- Bir nevi postanedeki "ayırma masası"

**2. Queue (Kuyruk)**
- Mesajların sırayla beklediği yer
- FIFO: İlk gelen ilk çıkar (First In, First Out)
- Bizim projede 3 kuyruk var:
  - `measurement.raw` → Ham sensör verisi
  - `measurement.featured` → Zenginleştirilmiş veri
  - `prediction.result` → ML tahmin sonucu

**3. Routing Key (Yönlendirme Anahtarı)**
- Exchange'e gelen mesajın HANGİ kuyruğa gideceğini belirler
- Bir nevi mektubun üzerindeki "adres"
- Örnek: Data Ingestion `measurement.raw` routing key'i ile gönderir →
  Exchange bunu `measurement.raw` kuyruğuna yönlendirir

**4. Binding (Bağlama)**
- Exchange ile Queue arasındaki bağlantıyı tanımlar
- "Bu routing key gelirse → şu kuyruğa at" demektir
- `definitions.json`'da tanımlı

**5. Producer / Consumer (Üretici / Tüketici)**
- **Producer**: Mesaj GÖNDEREN servis → Data Ingestion Service
- **Consumer**: Mesaj ALAN servis → Feature Service

#### WindSentinel'de RabbitMQ Akışı:

```
Data Ingestion Service                    Feature Service
    (Producer)                              (Consumer)
        │                                       │
        │  publish("measurement.raw", {...})     │
        │──────────────┐                         │
                       ▼                         │
              ┌─────────────────┐                │
              │  wind.events    │ (Exchange)      │
              │  (topic)        │                │
              └────────┬────────┘                │
                       │ routing_key =            │
                       │ "measurement.raw"        │
                       ▼                         │
              ┌─────────────────┐                │
              │ measurement.raw │ (Queue)         │
              │ [msg1, msg2...] │                 │
              └────────┬────────┘                │
                       │                         │
                       │     consume()           │
                       └────────────────────────>│
```

#### Neden Doğrudan HTTP Değil de RabbitMQ?

| Özellik | HTTP (Doğrudan) | RabbitMQ (Kuyruk) |
|---------|-----------------|-------------------|
| Bağımlılık | Alıcı AÇIK olmalı | Alıcı kapalıysa mesaj kuyrukta bekler |
| Hız | Cevap bekler (senkron) | Gönder ve unut (asenkron) |
| Yük | 1000 mesaj → 1000 HTTP isteği | 1000 mesaj → kuyrukta sırayla işlenir |
| Hata | Alıcı çökerse mesaj kaybolur | Mesaj kuyrukta güvende kalır |

---

### Kavram 3: Docker Container Nedir?

Her mikroservis kendi Docker container'ında çalışır. Container = uygulamanın çalışması için gereken HER ŞEYİ paketleyen kutu.

```
┌─────────────────────────────────┐
│  Docker Container               │
│  ┌───────────────────────────┐  │
│  │ Python 3.11               │  │
│  │ FastAPI + Pandas          │  │
│  │ data-ingestion-service    │  │
│  │ (main.py)                 │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

**Dockerfile** container'ın "tarifi":
1. Python 3.11 yükle
2. Gerekli kütüphaneleri yükle (pip install)
3. Kodumuzu kopyala
4. Uygulamayı başlat

---

### Adım 1: Dosya Yapısı Oluşturulması

```
services/data-ingestion-service/
├── Dockerfile          ← Container tarifi
├── requirements.txt    ← Python bağımlılıkları
├── config.py           ← Ortam değişkenleri (RabbitMQ URL vb.)
├── rabbitmq_client.py  ← RabbitMQ bağlantı & publish modülü
├── csv_reader.py       ← SCADA CSV okuyucu
└── main.py             ← FastAPI uygulaması (giriş noktası)
```

#### config.py — Ne İşe Yarar?
Ortam değişkenlerini (environment variables) tek yerden yönetir. Docker container'ı başlatırken `.env` dosyasındaki değerler otomatik olarak aktarılır:
- `RABBITMQ_URL` → RabbitMQ sunucusunun adresi
- `SCADA_DATA_PATH` → CSV dosyalarının yolu

#### rabbitmq_client.py — Ne İşe Yarar?
RabbitMQ ile ilgili tüm işlemleri yönetir:
- `connect()` → AMQP protokolü ile RabbitMQ'ya bağlan
- `publish(message)` → `wind.events` exchange'ine `measurement.raw` routing key ile mesaj gönder
- `close()` → Bağlantıyı kapat

**AMQP** = Advanced Message Queuing Protocol. RabbitMQ'nun konuştuğu dil. HTTP gibi bir protokol ama mesaj kuyruğu için özelleştirilmiş.

**aio-pika** = Python'da RabbitMQ ile konuşmak için kullandığımız kütüphane. "aio" = asyncio (asenkron), "pika" = RabbitMQ'nun Python client'ı.

#### csv_reader.py — Ne İşe Yarar?
SCADA CSV dosyalarını okur ve her satırı RabbitMQ mesaj formatına dönüştürür:
```
CSV satırı: 2021-08-03 06:10:00, 0, 1, train, 0, 22.0, 124.4, ...
                    ↓ dönüşüm
JSON mesaj: {"timestamp": "2021-08-03T06:10:00Z", "asset_id": 0, "wind_speed": 1.7, ...}
```

#### main.py — Ne İşe Yarar?
FastAPI uygulaması. HTTP endpoint'leri sunar:
- `POST /ingest` → Tek bir türbin CSV'sini oku ve RabbitMQ'ya gönder
- `GET /health` → Servis çalışıyor mu? Kontrol endpoint'i

---

*Bu log, yeni servisler geliştirildikçe güncellenecektir.*
