# Pipeline ile uyumlu feature listesi.
# 6 ham sensor (feature-selection.md 5-algoritma konsensus) + 4 turetilmis ozellik.
# Sutun sirasinin korunmasi modelin dogru tahmin yapmasi icin KRITIKTIR.

FEATURE_COLUMNS = [
    # 6 temel sensor (Data Ingestion -> Feature Service'den gecen)
    "wind_speed",                 # wind_speed_3_avg  (3/5 konsensus)
    "power_output",               # power_30_avg      (5/5 konsensus)
    "generator_rpm",              # sensor_18_avg     (4/5 konsensus)
    "total_active_power",         # sensor_50         (5/5 konsensus)
    "reactive_power_inductive",   # reactive_power_28 (4/5 konsensus)
    "reactive_power_capacitive",  # reactive_power_27 (4/5 konsensus)
    # 4 turetilmis ozellik (Feature Service'in urettigi)
    "power_factor",               # total_active_power / (inductive + capacitive)
    "rpm_ratio",                  # generator_rpm / rotor_rpm
    "reactive_power_balance",     # inductive - capacitive
    "power_to_wind_ratio",        # power_output / wind_speed
]

# Ensemble agirliklari (notebook'tan optimize edilmis)
# IsoForest=0.1, XGBoost=0.9
ISO_WEIGHT: float = 0.1
XGB_WEIGHT: float = 0.9

# Hibrit skor esik degerleri (PR curve'den hesaplanmis)
ANOMALY_THRESHOLD: float = 0.6859

# Alarm Severity Esikleri
SEVERITY_THRESHOLD_WARNING: float = 0.6859
SEVERITY_THRESHOLD_CRITICAL: float = 0.8546
