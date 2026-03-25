# Pipeline ile uyumlu feature listesi.
# 6 ham sensor + 4 turetilmis + 10 time-series = 20 feature
# Sutun sirasinin korunmasi modelin dogru tahmin yapmasi icin KRITIKTIR.

# Feature Service'den gelen base feature'lar
BASE_FEATURES = [
    "wind_speed", "power_output", "generator_rpm",
    "total_active_power", "reactive_power_inductive", "reactive_power_capacitive",
    "power_factor", "rpm_ratio", "reactive_power_balance", "power_to_wind_ratio",
]

# Time-series feature'lar (Prediction Service icinde hesaplanir)
TIME_SERIES_FEATURES = [
    "power_output_rolling_mean", "power_output_rolling_std", "power_output_delta",
    "generator_rpm_rolling_mean", "generator_rpm_rolling_std", "generator_rpm_delta",
    "wind_speed_rolling_mean", "wind_speed_rolling_std", "wind_speed_delta",
    "power_deviation",
    "power_curve_deviation",
]

# Model'in bekledigli tam feature listesi
FEATURE_COLUMNS = BASE_FEATURES + TIME_SERIES_FEATURES

# Rolling window boyutu (6 olcum = 1 saat, 10dk aralikli SCADA)
ROLLING_WINDOW = 6

# Ensemble agirliklari
ISO_WEIGHT: float = 0.50
XGB_WEIGHT: float = 0.50

# Esik degerleri (PR curve'den hesaplanmis - 21 feature, F1=0.61)
ANOMALY_THRESHOLD: float = 0.3533
SEVERITY_THRESHOLD_WARNING: float = 0.3533
SEVERITY_THRESHOLD_CRITICAL: float = 0.6418
