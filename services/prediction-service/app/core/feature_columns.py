# Feature Service'in ürettiği gerçek alanlarla eşleşen kolon listesi.
# Sütun sırasının korunması modelin doğru tahmin yapması için KRİTİKTİR.
#
# Bu liste feature-service/app/schemas.py → FeatureMessage ile uyumludur.
# Sayısal (numeric) alanlar seçilmiştir - meta alanlar (timestamp, turbine_id vb.) hariç.

FEATURE_COLUMNS = [
    "wind_speed",                 # Rüzgar hızı (m/s) - referans parametre
    "power_output",               # Şebeke gücü (kW) - en güçlü anomali göstergesi
    "generator_rpm",              # Jeneratör RPM - bearing arızası göstergesi
    "power_factor",               # Güç faktörü (türetilmiş)
    "rpm_ratio",                  # Jeneratör/Rotor RPM oranı (türetilmiş)
    "reactive_power_balance",     # Reaktif güç dengesi (türetilmiş)
    "power_to_wind_ratio",        # Rüzgar-güç verimliliği (türetilmiş)
]

# Hibrit skor (0.6*Iso + 0.4*XGB) için eşik değerleri.
ANOMALY_THRESHOLD: float = 0.63

# Alarm Severity Eşikleri
SEVERITY_THRESHOLD_CRITICAL: float = 0.90
SEVERITY_THRESHOLD_WARNING: float = 0.63
