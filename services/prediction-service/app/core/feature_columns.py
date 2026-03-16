# Bu dosya hem model eğitiminde hem de servis içinde ortak kullanılacaktır.
# Sütun sırasının (Feature Order) korunması modelin doğru tahmin yapması için KRİTİKTİR.

FEATURE_COLUMNS = [
    "wind_speed",
    "active_power",
    "wind_direction",
    "theoretical_power_curve",
    "wind_speed_rolling_mean",
    "wind_speed_rolling_std",
    "power_error"
]

# Hibrit skor (0.6*Iso + 0.4*XGB) için eşik değerleri.
# EDA aşamasında veriyle doğrulanıp güncellenmiştir.
ANOMALY_THRESHOLD: float = 0.63 # Genel anomali sınırı

# Alarm Severity Eşikleri
SEVERITY_THRESHOLD_CRITICAL: float = 0.90
SEVERITY_THRESHOLD_WARNING: float = 0.63
