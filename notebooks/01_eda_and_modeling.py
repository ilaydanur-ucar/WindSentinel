# %% [markdown]
# # WindSentinel - ML Model Eğitimi
# 5 algoritma ile seçilmiş 6 temel SCADA sensörü + 4 türetilmiş feature ile
# Isolation Forest + XGBoost eğitimi.

# %%
import pandas as pd
import numpy as np
import joblib
import os
import hashlib
import json

from sklearn.ensemble import IsolationForest
import xgboost as xgb
from sklearn.metrics import classification_report, precision_recall_curve, f1_score

import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────
# Pipeline ile uyumlu feature listesi
# 6 ham sensör (feature-selection.md konsensüsü) + 4 türetilmiş
# ─────────────────────────────────────────
FEATURE_COLUMNS = [
    # 6 temel sensör (Data Ingestion'dan gelen)
    "wind_speed",                 # wind_speed_3_avg  (3/5 konsensüs)
    "power_output",               # power_30_avg      (5/5 konsensüs)
    "generator_rpm",              # sensor_18_avg     (4/5 konsensüs)
    "total_active_power",         # sensor_50         (5/5 konsensüs)
    "reactive_power_inductive",   # reactive_power_28 (4/5 konsensüs)
    "reactive_power_capacitive",  # reactive_power_27 (4/5 konsensüs)
    # 4 türetilmiş özellik (Feature Service'in ürettiği)
    "power_factor",
    "rpm_ratio",
    "reactive_power_balance",
    "power_to_wind_ratio",
]

# %% [markdown]
# ## 1. Veriyi Yükleme
# Sadece 5 asıl türbin (asset_id: 0, 10, 11, 13, 21)

# %%
DATA_DIR = '../data/raw/Wind Farm A/datasets/'
TARGET_ASSETS = [0, 10, 11, 13, 21]

csv_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.csv') and not f.startswith('comma_')])

dfs = []
for csv_file in csv_files:
    path = os.path.join(DATA_DIR, csv_file)
    df_raw = pd.read_csv(path, sep=';')
    # Sadece hedef türbinleri al
    df_filtered = df_raw[df_raw['asset_id'].isin(TARGET_ASSETS)]
    if len(df_filtered) > 0:
        dfs.append(df_filtered)
        print(f"  {csv_file}: {len(df_filtered)} satır (asset_ids: {df_filtered['asset_id'].unique().tolist()})")

df_all = pd.concat(dfs, ignore_index=True)
print(f"\nToplam: {len(df_all)} satır")

# %% [markdown]
# ## 2. Feature Engineering (Pipeline ile aynı)

# %%
# Ham kolon seçimi (csv_reader.py COLUMN_MAPPING ile aynı)
df = pd.DataFrame({
    'timestamp': pd.to_datetime(df_all['time_stamp']),
    'asset_id': df_all['asset_id'].astype(int),
    'status_type_id': df_all['status_type_id'].astype(int),
    # 6 temel sensör
    'wind_speed': pd.to_numeric(df_all['wind_speed_3_avg'], errors='coerce'),
    'power_output': pd.to_numeric(df_all['power_30_avg'], errors='coerce'),
    'generator_rpm': pd.to_numeric(df_all['sensor_18_avg'], errors='coerce'),
    'total_active_power': pd.to_numeric(df_all.get('sensor_50_avg', df_all.get('sensor_50', 0)), errors='coerce'),
    'reactive_power_inductive': pd.to_numeric(df_all['reactive_power_28_avg'], errors='coerce'),
    'reactive_power_capacitive': pd.to_numeric(df_all['reactive_power_27_avg'], errors='coerce'),
    # Feature engineering için ek
    'rotor_rpm': pd.to_numeric(df_all.get('sensor_7_avg', 0), errors='coerce'),
})

df = df.sort_values('timestamp').reset_index(drop=True)
df = df.fillna(0)

# Feature Service'in türettiği 4 özellik (feature_engineer.py ile aynı mantık)
reactive_total = df['reactive_power_inductive'] + df['reactive_power_capacitive']
df['power_factor'] = np.where(reactive_total > 0, df['total_active_power'] / reactive_total, 0.0)
df['rpm_ratio'] = np.where(df['rotor_rpm'] > 0, df['generator_rpm'] / df['rotor_rpm'], 0.0)
df['reactive_power_balance'] = df['reactive_power_inductive'] - df['reactive_power_capacitive']
df['power_to_wind_ratio'] = np.where(df['wind_speed'] > 0, df['power_output'] / df['wind_speed'], 0.0)

# NaN/inf temizliği
df = df.replace([np.inf, -np.inf], np.nan)
df = df.dropna(subset=FEATURE_COLUMNS)

X = df[FEATURE_COLUMNS].copy()
print(f"Feature matrix: {X.shape}")
print(X.describe().round(4))

# %% [markdown]
# ## 3. Target Label (Gerçek arıza verileri)
# status_type_id > 0 → gerçek anomali

# %%
df['is_anomaly'] = (df['status_type_id'] > 0).astype(int)
y = df['is_anomaly']

print("Anomali Dağılımı:")
print(y.value_counts())
print(f"Anomali oranı: {y.mean():.2%}")

# %% [markdown]
# ## 4. Model Eğitimi

# %%
split_idx = int(len(df) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

print(f"Train: {len(X_train)} | Test: {len(X_test)}")
print(f"Train anomali: {y_train.mean():.2%} | Test anomali: {y_test.mean():.2%}")

# --- Isolation Forest (Unsupervised) ---
iso_forest = IsolationForest(
    n_estimators=200,
    contamination=0.10,
    max_features=0.8,
    random_state=42,
)
iso_forest.fit(X_train)

def get_iso_normalized(model, data):
    raw_scores = model.decision_function(data)
    return 1 / (1 + np.exp(raw_scores))

iso_test_scores = get_iso_normalized(iso_forest, X_test)

# --- XGBoost (Supervised) ---
pos_weight = len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1)
xgb_model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    random_state=42,
    eval_metric='logloss',
    scale_pos_weight=pos_weight,
)
xgb_model.fit(X_train, y_train)

xgb_test_probs = xgb_model.predict_proba(X_test)[:, 1]

# %% [markdown]
# ## 5. Ensemble & Optimal Threshold

# %%
hybrid_scores = (0.6 * iso_test_scores) + (0.4 * xgb_test_probs)

precision, recall, thresholds = precision_recall_curve(y_test, hybrid_scores)
f1_scores_arr = 2 * recall * precision / (recall + precision + 1e-8)
best_idx = np.argmax(f1_scores_arr)
optimal_threshold = float(thresholds[best_idx])

print(f"Optimal Threshold: {optimal_threshold:.4f}")
print(f"Max F1-Score: {f1_scores_arr[best_idx]:.4f}")

y_pred = (hybrid_scores > optimal_threshold).astype(int)
print("\n" + classification_report(y_test, y_pred, target_names=['Normal', 'Anomali']))

# Severity eşikleri
critical_threshold = float(np.percentile(hybrid_scores[y_test == 1], 90)) if y_test.sum() > 0 else 0.90
print(f"Severity Thresholds:")
print(f"  WARNING: > {optimal_threshold:.4f}")
print(f"  CRITICAL: > {critical_threshold:.4f}")

# %% [markdown]
# ## 6. Modelleri Kaydet

# %%
OUTPUT_DIR = '../services/prediction-service/models_data/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_with_checksum(model, filename, is_xgb=False):
    path = os.path.join(OUTPUT_DIR, filename)
    if is_xgb:
        model.save_model(path)
    else:
        joblib.dump(model, path)
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

checksums = {}
checksums['isolation_forest.pkl'] = save_with_checksum(iso_forest, 'isolation_forest.pkl')
checksums['xgboost_model.json'] = save_with_checksum(xgb_model, 'xgboost_model.json', is_xgb=True)

with open(os.path.join(OUTPUT_DIR, 'checksums.json'), 'w') as f:
    json.dump(checksums, f, indent=4)

print(f"\nModeller kaydedildi: {OUTPUT_DIR}")
print(f"\nfeature_columns.py'a yazılacak değerler:")
print(f"  ANOMALY_THRESHOLD = {optimal_threshold:.4f}")
print(f"  SEVERITY_THRESHOLD_WARNING = {optimal_threshold:.4f}")
print(f"  SEVERITY_THRESHOLD_CRITICAL = {critical_threshold:.4f}")
print(f"\nChecksums:\n{json.dumps(checksums, indent=2)}")
