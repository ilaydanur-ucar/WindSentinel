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

# Hibrit skor (0.6*Iso + 0.4*XGB) için eşik değeri. 
# EDA aşamasında veriyle doğrulanıp güncellenebilir.
ANOMALY_THRESHOLD: float = 0.63
