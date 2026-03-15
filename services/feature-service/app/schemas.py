# ────────────────────────────────────────────────────────────
# schemas.py — Veri Kontratları (Data Contracts) ve Güvenlik
# ────────────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   Servisler arası konuşulan dildir. Giriş mesajlarının
#   doğrulanması (validation) ve çıkış mesajlarının şekli
#   tamamen buradadır.
#
# OWASP A04 (Insecure Design):
#   - Pydantic kullanılarak Type Safety (Tip Güvenliği) garanti edilir.
#   - extra="forbid" kuralıyla payload injection saldırıları engellenir.
#
# DRY:
#   Aynı validasyon kodları yüzlerce satıra dağılmaz. Sadece
#   RawMeasurementMessage(**message_dict) denilir ve biter.
# ────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field


class RawMeasurementMessage(BaseModel):
    """
    Kuyruktan (measurement.raw) okunacak HAM VERİ mesaj formatı.
    Data Ingestion servisinin oluşturduğu "MeasurementMessage" şemasıyla
    birebir aynı sözleşmeye tabidir.
    """
    
    # ── Meta Bilgiler ──
    timestamp: str = Field(..., description="Ölçüm zamanı (ISO 8601)")
    asset_id: int = Field(..., description="Türbin asset numarası")
    turbine_id: str = Field(..., description="Türbin kodu (ör: WFA-T00)")
    status_type_id: int = Field(
        ...,
        description="Durum tipi (0=normal, diğerleri=arıza)",
    )
    
    # ── Ana Sensörler (Feature Engineer'ın kullanacakları) ──
    wind_speed: float = Field(..., description="Rüzgar hızı (m/s)")
    power_output: float = Field(..., description="Şebeke gücü (kW)")
    generator_rpm: float = Field(..., description="Jeneratör RPM")
    total_active_power: float = Field(..., description="Toplam aktif güç (Wh)")
    reactive_power_inductive: float = Field(..., description="İndüktif reaktif güç (kVAr)")
    reactive_power_capacitive: float = Field(..., description="Kapasitif reaktif güç (kVAr)")
    
    # ── Ek Sensörler ──
    rotor_rpm: float = Field(..., description="Rotor RPM")
    gearbox_oil_temp: float = Field(..., description="Dişli kutusu yağ sıcaklığı (°C)")

    class Config:
        extra = "forbid"  # Beklenmeyen alanları sil/reddet (OWASP koruması)


class FeatureMessage(BaseModel):
    """
    Zenginleştirilmiş verinin (measurement.features) ÇIKIŞ SÖZLEŞMESİ.
    Downstream servisler (Örn: Prediction Service) bu veri modeline 
    kesin olarak güvenebilir.
    """
    
    # ── Meta Bilgiler (Ham veriden aktarılır) ──
    timestamp: str
    asset_id: int
    turbine_id: str
    status_type_id: int
    
    # ── 6 Temel Özellik (Ham veriden aktarılır) ──
    wind_speed: float
    power_output: float
    generator_rpm: float
    total_active_power: float
    reactive_power_inductive: float
    reactive_power_capacitive: float

    # ── YENİ TÜRETİLEN ÖZELLİKLER (Feature Engineering Sonuçları) ──
    power_factor: float = Field(..., description="Güç faktörü (Power Output ile bağlantılı tahmin gücü)")
    rpm_ratio: float = Field(..., description="Jeneratör / Rotor RPM oranı")
    reactive_power_balance: float = Field(..., description="İndüktif ve Kapasitif reaktif güç dengesi")
    power_to_wind_ratio: float = Field(..., description="Rüzgar hızına göre üretilen güç verimliliği")

    class Config:
        extra = "forbid"
