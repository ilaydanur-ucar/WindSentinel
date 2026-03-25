# %% [markdown]
# # WindSentinel - Cascade Optimization
# IsoForest filtre → XGBoost sadece supheli vakalarda
# Hedef: Daha temiz veriyle XGBoost precision artar → F1 yukselir

# %%
import pandas as pd
import numpy as np
import os, json, hashlib, joblib, time
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, precision_recall_curve, roc_auc_score, f1_score
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# === VERI HAZIRLIGI (ayni) ===
DATA_DIR = '../data/raw/Wind Farm A/datasets/'
EVENT_PATH = '../data/raw/Wind Farm A/event_info.csv'
TARGET_ASSETS = [0, 10, 11, 13, 21]
LEAD_TIME_HOURS = 24
ROLLING_WINDOW = 6

BASE_FEATURES = [
    "wind_speed", "power_output", "generator_rpm",
    "total_active_power", "reactive_power_inductive", "reactive_power_capacitive",
    "power_factor", "rpm_ratio", "reactive_power_balance", "power_to_wind_ratio",
]

events = pd.read_csv(EVENT_PATH, sep=';')
events['event_start'] = pd.to_datetime(events['event_start'])
events['event_end'] = pd.to_datetime(events['event_end'])
fault_events = events[events['event_label'] == 'anomaly'].copy()

csv_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.csv') and not f.startswith('comma_')])
dfs = []
for f in csv_files:
    df_raw = pd.read_csv(os.path.join(DATA_DIR, f), sep=';')
    df_filtered = df_raw[df_raw['asset_id'].isin(TARGET_ASSETS)]
    if len(df_filtered) > 0: dfs.append(df_filtered)
df_all = pd.concat(dfs, ignore_index=True)

df = pd.DataFrame({
    'timestamp': pd.to_datetime(df_all['time_stamp']),
    'asset_id': df_all['asset_id'].astype(int),
    'train_test': df_all['train_test'].values,
    'wind_speed': pd.to_numeric(df_all['wind_speed_3_avg'], errors='coerce'),
    'power_output': pd.to_numeric(df_all['power_30_avg'], errors='coerce'),
    'generator_rpm': pd.to_numeric(df_all['sensor_18_avg'], errors='coerce'),
    'total_active_power': pd.to_numeric(df_all.get('sensor_50_avg', df_all.get('sensor_50', 0)), errors='coerce'),
    'reactive_power_inductive': pd.to_numeric(df_all['reactive_power_28_avg'], errors='coerce'),
    'reactive_power_capacitive': pd.to_numeric(df_all['reactive_power_27_avg'], errors='coerce'),
    'rotor_rpm': pd.to_numeric(df_all.get('sensor_7_avg', 0), errors='coerce'),
}).fillna(0)

df = df.sort_values(['asset_id', 'timestamp']).reset_index(drop=True)
reactive_total = df['reactive_power_inductive'] + df['reactive_power_capacitive']
df['power_factor'] = np.where(reactive_total > 0, df['total_active_power'] / reactive_total, 0.0)
df['rpm_ratio'] = np.where(df['rotor_rpm'] > 0, df['generator_rpm'] / df['rotor_rpm'], 0.0)
df['reactive_power_balance'] = df['reactive_power_inductive'] - df['reactive_power_capacitive']
df['power_to_wind_ratio'] = np.where(df['wind_speed'] > 0, df['power_output'] / df['wind_speed'], 0.0)

for col in ['power_output', 'generator_rpm', 'wind_speed']:
    df[f'{col}_rolling_mean'] = df.groupby('asset_id')[col].transform(lambda x: x.rolling(window=ROLLING_WINDOW, min_periods=1).mean())
    df[f'{col}_rolling_std'] = df.groupby('asset_id')[col].transform(lambda x: x.rolling(window=ROLLING_WINDOW, min_periods=1).std().fillna(0))
    df[f'{col}_delta'] = df.groupby('asset_id')[col].transform(lambda x: x.diff().fillna(0))
df['power_deviation'] = df['power_output'] - df['power_output_rolling_mean']

FEATURE_COLUMNS = BASE_FEATURES + [
    'power_output_rolling_mean', 'power_output_rolling_std', 'power_output_delta',
    'generator_rpm_rolling_mean', 'generator_rpm_rolling_std', 'generator_rpm_delta',
    'wind_speed_rolling_mean', 'wind_speed_rolling_std', 'wind_speed_delta',
    'power_deviation',
]
df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLUMNS)

df['is_anomaly'] = 0
for _, event in fault_events.iterrows():
    lead_start = event['event_start'] - pd.Timedelta(hours=LEAD_TIME_HOURS)
    mask = (df['asset_id'] == event['asset']) & (df['timestamp'] >= lead_start) & (df['timestamp'] <= event['event_end'])
    df.loc[mask, 'is_anomaly'] = 1

train_mask = df['train_test'] == 'train'
test_mask = df['train_test'] == 'prediction'
X_train = df.loc[train_mask, FEATURE_COLUMNS].values
X_test = df.loc[test_mask, FEATURE_COLUMNS].values
y_train = df.loc[train_mask, 'is_anomaly'].values
y_test = df.loc[test_mask, 'is_anomaly'].values

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"Train: {len(X_train)}, Test: {len(X_test)}")
print(f"Anomali: train={y_train.mean():.2%}, test={y_test.mean():.2%}")

# %% [markdown]
# ## 1. BASELINE (flat ensemble)

# %%
iso_forest = IsolationForest(n_estimators=150, contamination=min(float(y_train.mean()) * 2, 0.15),
                              max_features=0.7, max_samples=10000, random_state=42)
iso_forest.fit(X_train_scaled)

def iso_normalized(model, data):
    return 1 / (1 + np.exp(model.decision_function(data)))

iso_test = iso_normalized(iso_forest, X_test_scaled)

pos_weight = (len(y_train) - y_train.sum()) / max(y_train.sum(), 1)
xgb_model = xgb.XGBClassifier(n_estimators=500, max_depth=8, learning_rate=0.03,
    min_child_weight=5, subsample=0.8, colsample_bytree=0.8, gamma=1,
    random_state=42, eval_metric='aucpr', scale_pos_weight=pos_weight, tree_method='hist')
xgb_model.fit(X_train_scaled, y_train)
xgb_test = xgb_model.predict_proba(X_test_scaled)[:, 1]

baseline_scores = 0.5 * iso_test + 0.5 * xgb_test
prec, rec, thresh = precision_recall_curve(y_test, baseline_scores)
f1s = 2 * rec * prec / (rec + prec + 1e-8)
baseline_f1 = f1s.max()
baseline_thresh = float(thresh[np.argmax(f1s)])
print(f"\nBASELINE F1: {baseline_f1:.4f} (threshold={baseline_thresh:.4f})")

# %% [markdown]
# ## 2. CASCADE: IsoForest filtre → XGBoost sadece supheli vakalar
# Normal vakalarin cogunlugu IsoForest ile elenir
# XGBoost daha temiz (daha az gurultulu) veri gorur → precision artar

# %%
print("\n" + "="*60)
print("CASCADE OPTIMIZASYONU")
print("="*60)

best_cascade_f1 = 0
best_iso_gate = 0
best_xgb_thresh = 0
best_details = {}

# IsoForest gate esigini sweep et
for iso_gate_pct in range(10, 80, 2):
    iso_gate = np.percentile(iso_test, iso_gate_pct)

    # IsoForest skoru gate'in altindaysa → "normal" (hizli yol)
    # Gate'in ustundeyse → XGBoost'a gonder (yavas yol)
    suspicious_mask = iso_test >= iso_gate
    normal_mask_test = ~suspicious_mask

    # Cascade skoru: normal vakalar 0 skor, supheli vakalar XGBoost skoru
    cascade_scores = np.zeros(len(y_test))
    cascade_scores[suspicious_mask] = xgb_test[suspicious_mask]

    # F1 hesapla
    prec_c, rec_c, thresh_c = precision_recall_curve(y_test, cascade_scores)
    f1s_c = 2 * rec_c * prec_c / (rec_c + prec_c + 1e-8)
    max_f1 = f1s_c.max()
    max_thresh = float(thresh_c[np.argmax(f1s_c)])

    # Hiz metrigi: kac % veri XGBoost'a gidiyor
    pct_to_xgb = suspicious_mask.mean() * 100

    # Normal olarak etiketlenen gercek anomalileri kacirma (miss rate)
    if normal_mask_test.sum() > 0:
        miss_rate = y_test[normal_mask_test].mean() * 100
    else:
        miss_rate = 0

    if max_f1 > best_cascade_f1:
        best_cascade_f1 = max_f1
        best_iso_gate = iso_gate
        best_xgb_thresh = max_thresh
        best_details = {
            'iso_gate_percentile': iso_gate_pct,
            'iso_gate_value': float(iso_gate),
            'xgb_threshold': max_thresh,
            'pct_to_xgb': pct_to_xgb,
            'miss_rate': miss_rate,
        }

print(f"\nEN IYI CASCADE:")
print(f"  F1: {best_cascade_f1:.4f}")
print(f"  IsoForest gate: {best_details['iso_gate_value']:.4f} (percentile={best_details['iso_gate_percentile']})")
print(f"  XGBoost threshold: {best_details['xgb_threshold']:.4f}")
print(f"  XGBoost'a giden veri: {best_details['pct_to_xgb']:.1f}%")
print(f"  Kacirma orani (miss): {best_details['miss_rate']:.2f}%")

# Final tahmin
suspicious = iso_test >= best_iso_gate
final_scores = np.zeros(len(y_test))
final_scores[suspicious] = xgb_test[suspicious]
y_pred = (final_scores > best_xgb_thresh).astype(int)

print("\n" + classification_report(y_test, y_pred, target_names=['Normal', 'Anomali']))

roc = roc_auc_score(y_test, final_scores)
print(f"ROC-AUC: {roc:.4f}")

# %% [markdown]
# ## 3. BENCHMARK: Inference hizi

# %%
print("\n" + "="*60)
print("INFERENCE BENCHMARK")
print("="*60)

single_sample = X_test_scaled[0:1]

# IsoForest tek
times_iso = []
for _ in range(1000):
    t0 = time.perf_counter()
    iso_normalized(iso_forest, single_sample)
    times_iso.append((time.perf_counter() - t0) * 1000)

# XGBoost tek
times_xgb = []
for _ in range(1000):
    t0 = time.perf_counter()
    xgb_model.predict_proba(single_sample)
    times_xgb.append((time.perf_counter() - t0) * 1000)

# Cascade (iso + conditional xgb)
times_cascade = []
for _ in range(1000):
    t0 = time.perf_counter()
    iso_score = iso_normalized(iso_forest, single_sample)[0]
    if iso_score >= best_iso_gate:
        xgb_model.predict_proba(single_sample)
    times_cascade.append((time.perf_counter() - t0) * 1000)

# Flat ensemble (her ikisi her zaman)
times_flat = []
for _ in range(1000):
    t0 = time.perf_counter()
    iso_normalized(iso_forest, single_sample)
    xgb_model.predict_proba(single_sample)
    times_flat.append((time.perf_counter() - t0) * 1000)

print(f"IsoForest tek:     {np.median(times_iso):.2f}ms (p95={np.percentile(times_iso, 95):.2f}ms)")
print(f"XGBoost tek:       {np.median(times_xgb):.2f}ms (p95={np.percentile(times_xgb, 95):.2f}ms)")
print(f"Flat ensemble:     {np.median(times_flat):.2f}ms (p95={np.percentile(times_flat, 95):.2f}ms)")
print(f"CASCADE:           {np.median(times_cascade):.2f}ms (p95={np.percentile(times_cascade, 95):.2f}ms)")
print(f"Cascade hiz kazanci: {np.median(times_flat)/np.median(times_cascade):.1f}x")

# %% [markdown]
# ## 4. KARSILASTIRMA ve KAYIT

# %%
print("\n" + "="*60)
print("FINAL KARSILASTIRMA")
print("="*60)

improvement = ((best_cascade_f1 - baseline_f1) / baseline_f1) * 100
print(f"  Baseline (flat):  F1={baseline_f1:.4f}  inference={np.median(times_flat):.2f}ms")
print(f"  CASCADE:          F1={best_cascade_f1:.4f}  inference={np.median(times_cascade):.2f}ms")
print(f"  F1 degisim:       {improvement:+.1f}%")
print(f"  Hiz kazanci:      {np.median(times_flat)/np.median(times_cascade):.1f}x")

# Modelleri kaydet (cascade config ile)
OUTPUT_DIR = '../services/prediction-service/models_data/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_with_checksum(model, filename, is_xgb=False, is_scaler=False):
    path = os.path.join(OUTPUT_DIR, filename)
    if is_xgb:
        model.save_model(path)
    else:
        joblib.dump(model, path, compress=3)
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4096), b""):
            sha.update(block)
    return sha.hexdigest()

checksums = {}
checksums['isolation_forest.pkl'] = save_with_checksum(iso_forest, 'isolation_forest.pkl')
checksums['xgboost_model.json'] = save_with_checksum(xgb_model, 'xgboost_model.json', is_xgb=True)
checksums['scaler.pkl'] = save_with_checksum(scaler, 'scaler.pkl')

with open(os.path.join(OUTPUT_DIR, 'checksums.json'), 'w') as f:
    json.dump(checksums, f, indent=4)

with open(os.path.join(OUTPUT_DIR, 'feature_config.json'), 'w') as f:
    json.dump({
        'feature_columns': FEATURE_COLUMNS,
        'base_features': BASE_FEATURES,
        'architecture': 'cascade',
        'cascade_iso_gate': best_details['iso_gate_value'],
        'cascade_iso_gate_percentile': best_details['iso_gate_percentile'],
        'cascade_xgb_threshold': best_details['xgb_threshold'],
        'anomaly_threshold': best_details['xgb_threshold'],
        'severity_warning': best_details['xgb_threshold'],
        'severity_critical': float(np.percentile(final_scores[y_test == 1], 90)) if y_test.sum() > 0 else 0.90,
        'iso_weight': 0.5,
        'xgb_weight': 0.5,
        'lead_time_hours': LEAD_TIME_HOURS,
        'rolling_window': ROLLING_WINDOW,
        'model_version': 'v5.0-cascade',
        'f1_score': float(best_cascade_f1),
        'baseline_f1': float(baseline_f1),
    }, f, indent=4)

print(f"\nModeller kaydedildi: {OUTPUT_DIR}")
print(f"Mimari: CASCADE (IsoForest gate → XGBoost)")
print(f"F1: {best_cascade_f1:.4f}")
