# %% [markdown]
# # WindSentinel - ML Model Egitimi (Lead Time Window + Stratified Split)

# %%
import pandas as pd
import numpy as np
import joblib
import os
import hashlib
import json

from sklearn.ensemble import IsolationForest
from sklearn.model_selection import StratifiedShuffleSplit
import xgboost as xgb
from sklearn.metrics import classification_report, precision_recall_curve

import warnings
warnings.filterwarnings('ignore')

FEATURE_COLUMNS = [
    "wind_speed", "power_output", "generator_rpm",
    "total_active_power", "reactive_power_inductive", "reactive_power_capacitive",
    "power_factor", "rpm_ratio", "reactive_power_balance", "power_to_wind_ratio",
]

LEAD_TIME_HOURS = 24

# %% [markdown]
# ## 1. Veri Yukleme

# %%
DATA_DIR = '../data/raw/Wind Farm A/datasets/'
EVENT_PATH = '../data/raw/Wind Farm A/event_info.csv'
TARGET_ASSETS = [0, 10, 11, 13, 21]

events = pd.read_csv(EVENT_PATH, sep=';')
events['event_start'] = pd.to_datetime(events['event_start'])
events['event_end'] = pd.to_datetime(events['event_end'])
fault_events = events[events['event_label'] == 'anomaly'].copy()
print(f"Ariza olaylari: {len(fault_events)}")

csv_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.csv') and not f.startswith('comma_')])
dfs = []
for csv_file in csv_files:
    df_raw = pd.read_csv(os.path.join(DATA_DIR, csv_file), sep=';')
    df_filtered = df_raw[df_raw['asset_id'].isin(TARGET_ASSETS)]
    if len(df_filtered) > 0:
        dfs.append(df_filtered)
df_all = pd.concat(dfs, ignore_index=True)
print(f"SCADA kayit: {len(df_all)}")

# %% [markdown]
# ## 2. Feature Engineering

# %%
df = pd.DataFrame({
    'timestamp': pd.to_datetime(df_all['time_stamp']),
    'asset_id': df_all['asset_id'].astype(int),
    'status_type_id': df_all['status_type_id'].astype(int),
    'wind_speed': pd.to_numeric(df_all['wind_speed_3_avg'], errors='coerce'),
    'power_output': pd.to_numeric(df_all['power_30_avg'], errors='coerce'),
    'generator_rpm': pd.to_numeric(df_all['sensor_18_avg'], errors='coerce'),
    'total_active_power': pd.to_numeric(df_all.get('sensor_50_avg', df_all.get('sensor_50', 0)), errors='coerce'),
    'reactive_power_inductive': pd.to_numeric(df_all['reactive_power_28_avg'], errors='coerce'),
    'reactive_power_capacitive': pd.to_numeric(df_all['reactive_power_27_avg'], errors='coerce'),
    'rotor_rpm': pd.to_numeric(df_all.get('sensor_7_avg', 0), errors='coerce'),
})
df = df.sort_values('timestamp').reset_index(drop=True).fillna(0)

reactive_total = df['reactive_power_inductive'] + df['reactive_power_capacitive']
df['power_factor'] = np.where(reactive_total > 0, df['total_active_power'] / reactive_total, 0.0)
df['rpm_ratio'] = np.where(df['rotor_rpm'] > 0, df['generator_rpm'] / df['rotor_rpm'], 0.0)
df['reactive_power_balance'] = df['reactive_power_inductive'] - df['reactive_power_capacitive']
df['power_to_wind_ratio'] = np.where(df['wind_speed'] > 0, df['power_output'] / df['wind_speed'], 0.0)

df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLUMNS)
X = df[FEATURE_COLUMNS].copy()

# %% [markdown]
# ## 3. Lead Time Window Etiketleme

# %%
df['is_anomaly'] = 0
for _, event in fault_events.iterrows():
    asset = event['asset']
    start = event['event_start']
    end = event['event_end']
    lead_start = start - pd.Timedelta(hours=LEAD_TIME_HOURS)
    mask = (df['asset_id'] == asset) & (df['timestamp'] >= lead_start) & (df['timestamp'] <= end)
    df.loc[mask, 'is_anomaly'] = 1

y = df['is_anomaly']
print(f"Anomali orani: {y.mean():.2%} ({y.sum()} / {len(y)})")

# %% [markdown]
# ## 4. Stratified Split + Model Egitimi

# %%
# Stratified split: train ve test'te anomali orani esit
sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(sss.split(X, y))

X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

print(f"Train: {len(X_train)} (anomali: {y_train.mean():.2%})")
print(f"Test:  {len(X_test)} (anomali: {y_test.mean():.2%})")

# --- Isolation Forest ---
iso_forest = IsolationForest(
    n_estimators=200,
    contamination=float(y_train.mean()),
    max_features=0.8,
    random_state=42,
)
iso_forest.fit(X_train)

def get_iso_normalized(model, data):
    raw_scores = model.decision_function(data)
    return 1 / (1 + np.exp(raw_scores))

iso_test_scores = get_iso_normalized(iso_forest, X_test)

# --- XGBoost ---
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
# ## 5. En Iyi Ensemble Agirligi + Threshold

# %%
best_f1 = 0
best_weight = 0
best_threshold = 0
best_scores = None

for iso_w_int in range(0, 7):
    iso_w = iso_w_int / 10.0
    xgb_w = 1.0 - iso_w
    scores = (iso_w * iso_test_scores) + (xgb_w * xgb_test_probs)
    prec, rec, thresh = precision_recall_curve(y_test, scores)
    f1s = 2 * rec * prec / (rec + prec + 1e-8)
    idx = np.argmax(f1s)
    if f1s[idx] > best_f1:
        best_f1 = f1s[idx]
        best_weight = iso_w
        best_threshold = float(thresh[idx])
        best_scores = scores

print(f"En iyi: IsoForest={best_weight:.1f}, XGBoost={1-best_weight:.1f}")
print(f"F1={best_f1:.4f}, Threshold={best_threshold:.4f}")

hybrid_scores = best_scores
optimal_threshold = best_threshold

y_pred = (hybrid_scores > optimal_threshold).astype(int)
print("\n" + classification_report(y_test, y_pred, target_names=['Normal', 'Anomali']))

critical_threshold = float(np.percentile(hybrid_scores[y_test == 1], 90)) if y_test.sum() > 0 else 0.90
print(f"WARNING:  > {optimal_threshold:.4f}")
print(f"CRITICAL: > {critical_threshold:.4f}")

# %% [markdown]
# ## 6. Kaydet

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

print(f"\nModeller kaydedildi.")
print(f"ANOMALY_THRESHOLD = {optimal_threshold:.4f}")
print(f"SEVERITY_THRESHOLD_WARNING = {optimal_threshold:.4f}")
print(f"SEVERITY_THRESHOLD_CRITICAL = {critical_threshold:.4f}")
print(f"ISO_WEIGHT = {best_weight:.1f}")
print(f"XGB_WEIGHT = {1-best_weight:.1f}")
print(f"\nChecksums:\n{json.dumps(checksums, indent=2)}")
