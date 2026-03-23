-- WindSentinel PostgreSQL Initial Schema

-- Kullanıcılar tablosu
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Türbinler tablosu
CREATE TABLE IF NOT EXISTS turbines (
    id SERIAL PRIMARY KEY,
    turbine_id VARCHAR(20) UNIQUE NOT NULL,
    asset_id INTEGER NOT NULL,
    farm_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'online',
    CONSTRAINT chk_turbine_status CHECK (status IN ('online', 'offline', 'maintenance'))
);

-- Alert'ler tablosu
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    turbine_id VARCHAR(20) NOT NULL REFERENCES turbines(turbine_id),
    asset_id INTEGER NOT NULL,
    anomaly_type VARCHAR(100) NOT NULL,
    anomaly_score FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by INTEGER REFERENCES users(id),
    CONSTRAINT chk_anomaly_score CHECK (anomaly_score >= 0.0 AND anomaly_score <= 1.0),
    CONSTRAINT chk_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT chk_alert_status CHECK (status IN ('active', 'resolved')),
    CONSTRAINT chk_resolved_date CHECK (
        (status = 'active' AND resolved_at IS NULL) OR
        (status = 'resolved' AND resolved_at IS NOT NULL)
    )
);

-- Sık sorgulanan kolonlara index
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_turbine_id ON alerts(turbine_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);

-- Wind Farm A türbinlerini ekle
INSERT INTO turbines (turbine_id, asset_id, farm_name) VALUES
    ('WFA-T00', 0, 'Wind Farm A'),
    ('WFA-T10', 10, 'Wind Farm A'),
    ('WFA-T11', 11, 'Wind Farm A'),
    ('WFA-T13', 13, 'Wind Farm A'),
    ('WFA-T21', 21, 'Wind Farm A')
ON CONFLICT (turbine_id) DO NOTHING;

-- ─────────────────────────────────────────
-- Seed Data: Test verileri
-- Postman ve frontend geliştirme için örnek veri
-- ─────────────────────────────────────────

-- Test kullanıcıları (şifreler bcrypt ile hashlenmiştir)
INSERT INTO users (email, password, name) VALUES
    ('admin@windsentinel.com', '$2a$10$xKB8cKQ5z5lD8nK8hE8XxeQJ1r7M5VnQp3C8z4HkJvX5j9VqKhGy', 'Admin User'),
    ('technician@windsentinel.com', '$2a$10$xKB8cKQ5z5lD8nK8hE8XxeQJ1r7M5VnQp3C8z4HkJvX5j9VqKhGy', 'Saha Teknisyeni')
ON CONFLICT (email) DO NOTHING;

-- Örnek alertler (active)
INSERT INTO alerts (turbine_id, asset_id, anomaly_type, anomaly_score, confidence, status, created_at) VALUES
    ('WFA-T00', 0, 'Generator bearing failure', 0.87, 0.92, 'active', NOW() - INTERVAL '2 hours'),
    ('WFA-T10', 10, 'Gearbox failure', 0.76, 0.85, 'active', NOW() - INTERVAL '5 hours'),
    ('WFA-T13', 13, 'Hydraulic group', 0.91, 0.95, 'active', NOW() - INTERVAL '30 minutes')
ON CONFLICT DO NOTHING;

-- Örnek alertler (resolved - resolved_at zorunlu)
INSERT INTO alerts (turbine_id, asset_id, anomaly_type, anomaly_score, confidence, status, created_at, resolved_at) VALUES
    ('WFA-T11', 11, 'Transformer failure', 0.65, 0.78, 'resolved', NOW() - INTERVAL '1 day', NOW() - INTERVAL '20 hours'),
    ('WFA-T21', 21, 'Gearbox bearings damaged', 0.58, 0.71, 'resolved', NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days 20 hours')
ON CONFLICT DO NOTHING;
