# WindSentinel - API Kontratları

## Mikroservis Sınırları

```
┌─────────────────────────────────────────────────────────────┐
│                      Mobile App (Expo)                       │
│                    React Native + WebSocket                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / WS
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   API Gateway (:8000)                         │
│              Express.js + JWT Auth + REST                     │
└──────┬──────────┬──────────────┬────────────────┬────────────┘
       │          │              │                │
       ▼          ▼              ▼                ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────────┐
│  Data    │ │ Feature  │ │  Prediction  │ │  Notification    │
│ Ingestion│ │ Service  │ │  Service     │ │  Service (:8003) │
│ Service  │ │          │ │              │ │  WebSocket       │
└────┬─────┘ └────┬─────┘ └──────┬───────┘ └───────┬──────────┘
     │            │              │                  │
     └────────────┴──────────────┴──────────────────┘
                           │
                    ┌──────┴──────┐
                    │  RabbitMQ   │
                    │  (:5672)    │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ PostgreSQL  │
                    │  (:5434)    │
                    └─────────────┘
```

---

## 1. Data Ingestion Service (Python/FastAPI)

SCADA CSV dosyalarını okur, parse eder ve RabbitMQ'ya publish eder.

### RabbitMQ Publish

| Alan          | Değer                          |
|---------------|--------------------------------|
| Exchange      | `wind.events`                  |
| Routing Key   | `measurement.raw`              |
| Queue         | `measurement.raw`              |

### Mesaj Formatı (measurement.raw)

```json
{
  "timestamp": "2023-08-03T06:10:00Z",
  "asset_id": 0,
  "turbine_id": "WFA-T00",
  "wind_speed": 1.7,
  "power_output": -0.003756,
  "generator_rpm": 35.3,
  "rotor_rpm": 0.0,
  "gearbox_oil_temp": 41.0,
  "status_type_id": 0
}
```

---

## 2. Feature Service (Python/FastAPI)

RabbitMQ'dan ham veriyi consume eder, feature engineering yapar, zenginleştirilmiş veriyi tekrar publish eder.

### RabbitMQ Consume / Publish

| Alan          | Consume              | Publish                 |
|---------------|----------------------|-------------------------|
| Queue         | `measurement.raw`    | `measurement.featured`  |
| Routing Key   | `measurement.raw`    | `measurement.featured`  |

### Mesaj Formatı (measurement.featured)

```json
{
  "timestamp": "2023-08-03T06:10:00Z",
  "asset_id": 0,
  "turbine_id": "WFA-T00",
  "wind_speed": 1.7,
  "power_output": -0.003756,
  "generator_rpm": 35.3,
  "rotor_rpm": 0.0,
  "gearbox_oil_temp": 41.0,
  "power_coefficient": 0.0,
  "rpm_ratio": 0.0,
  "temp_delta": 2.0,
  "rolling_avg_power": -0.002,
  "rolling_std_wind": 0.65
}
```

---

## 3. Prediction Service (Python/FastAPI)

Feature verisini consume eder, anomali tahmini yapar, sonucu publish eder.

### RabbitMQ Consume / Publish

| Alan          | Consume                 | Publish                |
|---------------|-------------------------|------------------------|
| Queue         | `measurement.featured`  | `prediction.result`    |
| Routing Key   | `measurement.featured`  | `prediction.result`    |

### Mesaj Formatı (prediction.result)

```json
{
  "timestamp": "2023-08-03T06:10:00Z",
  "asset_id": 0,
  "turbine_id": "WFA-T00",
  "anomaly_score": 0.12,
  "is_anomaly": false,
  "anomaly_type": null,
  "confidence": 0.88,
  "features_used": {
    "wind_speed": 1.7,
    "power_output": -0.003756,
    "generator_rpm": 35.3,
    "rotor_rpm": 0.0,
    "gearbox_oil_temp": 41.0
  }
}
```

---

## 4. Notification Service (Node.js/Express)

Prediction sonuçlarını consume eder, anomali varsa PostgreSQL'e kaydeder ve WebSocket ile mobile app'e push eder.

### RabbitMQ Consume

| Alan          | Değer                |
|---------------|----------------------|
| Queue         | `prediction.result`  |
| Routing Key   | `prediction.result`  |

### REST API

| Method | Endpoint              | Açıklama                    |
|--------|-----------------------|-----------------------------|
| GET    | `/alerts`             | Tüm alert'leri listele      |
| GET    | `/alerts/:id`         | Tek alert detayı             |
| GET    | `/alerts/active`      | Aktif (çözülmemiş) alert'ler |

### WebSocket Event

```json
{
  "event": "new_alert",
  "data": {
    "id": 1,
    "turbine_id": "WFA-T00",
    "anomaly_type": "Generator bearing failure",
    "anomaly_score": 0.87,
    "timestamp": "2023-08-06T06:10:00Z",
    "status": "active"
  }
}
```

---

## 5. API Gateway (Node.js/Express)

Tüm servislere tek giriş noktası. JWT authentication + routing.

### Auth Endpoints

| Method | Endpoint         | Body                              | Açıklama       |
|--------|------------------|-----------------------------------|----------------|
| POST   | `/auth/login`    | `{ email, password }`             | JWT token al   |
| POST   | `/auth/register` | `{ email, password, name }`       | Kayıt ol       |

### Proxy Endpoints

| Method | Endpoint                  | Proxy To                          |
|--------|---------------------------|-----------------------------------|
| GET    | `/api/alerts`             | notification-service `/alerts`    |
| GET    | `/api/alerts/active`      | notification-service `/alerts/active` |
| GET    | `/api/turbines`           | PostgreSQL'den türbin listesi     |
| GET    | `/api/turbines/:id/stats` | PostgreSQL'den türbin istatistik  |

### JWT Token Formatı

```json
{
  "userId": 1,
  "email": "user@windsentinel.com",
  "iat": 1700000000,
  "exp": 1700086400
}
```

---

## RabbitMQ Queue Topolojisi

```
                    wind.events (topic exchange)
                           │
              ┌────────────┼────────────────┐
              │            │                │
              ▼            ▼                ▼
     measurement.raw  measurement.featured  prediction.result
         │                  │                    │
         ▼                  ▼                    ▼
   Feature Service   Prediction Service   Notification Service
```

---

## Veritabanı Şeması (PostgreSQL)

### users

| Kolon      | Tip          | Açıklama        |
|------------|--------------|-----------------|
| id         | SERIAL PK    | Otomatik ID     |
| email      | VARCHAR(255) | Unique email    |
| password   | VARCHAR(255) | Hashed password |
| name       | VARCHAR(100) | Kullanıcı adı   |
| created_at | TIMESTAMP    | Kayıt tarihi    |

### alerts

| Kolon         | Tip          | Açıklama               |
|---------------|--------------|------------------------|
| id            | SERIAL PK    | Otomatik ID            |
| turbine_id    | VARCHAR(20)  | Türbin kodu            |
| asset_id      | INTEGER      | Asset numarası         |
| anomaly_type  | VARCHAR(100) | Arıza tipi             |
| anomaly_score | FLOAT        | Anomali skoru (0-1)    |
| confidence    | FLOAT        | Model güven skoru      |
| status        | VARCHAR(20)  | active / resolved      |
| created_at    | TIMESTAMP    | Tespit zamanı          |
| resolved_at   | TIMESTAMP    | Çözüm zamanı (nullable)|

### turbines

| Kolon      | Tip          | Açıklama            |
|------------|--------------|---------------------|
| id         | SERIAL PK    | Otomatik ID         |
| turbine_id | VARCHAR(20)  | Türbin kodu (unique)|
| asset_id   | INTEGER      | Asset numarası      |
| farm_name  | VARCHAR(50)  | Çiftlik adı         |
| status     | VARCHAR(20)  | online / offline    |
