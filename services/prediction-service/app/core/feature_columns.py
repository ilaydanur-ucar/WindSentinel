# Pipeline ile uyumlu feature listesi.
# 6 ham sensör (feature-selection.md 5-algoritma konsensüsü) + 4 türetilmiş özellik.
# Sütun sırasının korunması modelin doğru tahmin yapması için KRİTİKTİR.

FEATURE_COLUMNS = [
    # 6 temel sensör (Data Ingestion → Feature Service'den geçen)
    "wind_speed",                 # wind_speed_3_avg  (3/5 konsensüs)
    "power_output",               # power_30_avg      (5/5 konsensüs)
    "generator_rpm",              # sensor_18_avg     (4/5 konsensüs)
    "total_active_power",         # sensor_50         (5/5 konsensüs)
    "reactive_power_inductive",   # reactive_power_28 (4/5 konsensüs)
    "reactive_power_capacitive",  # reactive_power_27 (4/5 konsensüs)
    # 4 türetilmiş özellik (Feature Service'in ürettiği)
    "power_factor",               # total_active_power / (inductive + capacitive)
    "rpm_ratio",                  # generator_rpm / rotor_rpm
    "reactive_power_balance",     # inductive - capacitive
    "power_to_wind_ratio",        # power_output / wind_speed
]

# Hibrit skor (0.6*IsoForest + 0.4*XGBoost) eşik değerleri
# 01_eda_and_modeling.py'dan hesaplanmış optimal değerler
ANOMALY_THRESHOLD: float = 0.5068

# Alarm Severity Eşikleri
SEVERITY_THRESHOLD_WARNING: float = 0.5068
SEVERITY_THRESHOLD_CRITICAL: float = 0.6035
