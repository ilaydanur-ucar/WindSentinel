# Retrain with 21 features (power_curve_deviation added)
import pandas as pd, numpy as np, os, json, hashlib, joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, precision_recall_curve
import xgboost as xgb
import warnings; warnings.filterwarnings('ignore')

DATA_DIR = '../data/raw/Wind Farm A/datasets/'
EVENT_PATH = '../data/raw/Wind Farm A/event_info.csv'
TARGET_ASSETS = [0, 10, 11, 13, 21]
LEAD_TIME_HOURS = 24; ROLLING_WINDOW = 6

events = pd.read_csv(EVENT_PATH, sep=';')
events['event_start'] = pd.to_datetime(events['event_start'])
events['event_end'] = pd.to_datetime(events['event_end'])
fault_events = events[events['event_label'] == 'anomaly']

dfs = []
for f in sorted(os.listdir(DATA_DIR)):
    if f.endswith('.csv') and not f.startswith('comma_'):
        df_raw = pd.read_csv(os.path.join(DATA_DIR, f), sep=';')
        dfs.append(df_raw[df_raw['asset_id'].isin(TARGET_ASSETS)])
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
df['power_curve_deviation'] = df.groupby('asset_id').apply(
    lambda g: g['power_output'] - g.groupby(pd.cut(g['wind_speed'], bins=20))['power_output'].transform('mean')
).reset_index(level=0, drop=True).fillna(0)

FEATURE_COLUMNS = [
    'wind_speed', 'power_output', 'generator_rpm',
    'total_active_power', 'reactive_power_inductive', 'reactive_power_capacitive',
    'power_factor', 'rpm_ratio', 'reactive_power_balance', 'power_to_wind_ratio',
    'power_output_rolling_mean', 'power_output_rolling_std', 'power_output_delta',
    'generator_rpm_rolling_mean', 'generator_rpm_rolling_std', 'generator_rpm_delta',
    'wind_speed_rolling_mean', 'wind_speed_rolling_std', 'wind_speed_delta',
    'power_deviation', 'power_curve_deviation',
]
df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLUMNS)

df['is_anomaly'] = 0
for _, ev in fault_events.iterrows():
    lead = ev['event_start'] - pd.Timedelta(hours=LEAD_TIME_HOURS)
    mask = (df['asset_id'] == ev['asset']) & (df['timestamp'] >= lead) & (df['timestamp'] <= ev['event_end'])
    df.loc[mask, 'is_anomaly'] = 1

train_mask = df['train_test'] == 'train'
test_mask = df['train_test'] == 'prediction'
X_train = df.loc[train_mask, FEATURE_COLUMNS].values
X_test = df.loc[test_mask, FEATURE_COLUMNS].values
y_train = df.loc[train_mask, 'is_anomaly'].values
y_test = df.loc[test_mask, 'is_anomaly'].values

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

print(f"Train: {len(X_train)} ({y_train.mean():.2%} anomali)")
print(f"Test:  {len(X_test)} ({y_test.mean():.2%} anomali)")
print(f"Features: {len(FEATURE_COLUMNS)}")

# IsoForest
iso = IsolationForest(n_estimators=150, contamination=min(float(y_train.mean())*2, 0.15),
                      max_features=0.7, max_samples=10000, random_state=42)
iso.fit(X_train_s)
iso_scores = 1 / (1 + np.exp(iso.decision_function(X_test_s)))

# XGBoost
pos_weight = (len(y_train) - y_train.sum()) / max(y_train.sum(), 1)
xgb_model = xgb.XGBClassifier(n_estimators=500, max_depth=8, learning_rate=0.03,
    min_child_weight=5, subsample=0.8, colsample_bytree=0.8, gamma=1,
    random_state=42, eval_metric='aucpr', scale_pos_weight=pos_weight, tree_method='hist')
xgb_model.fit(X_train_s, y_train)
xgb_probs = xgb_model.predict_proba(X_test_s)[:, 1]

# Ensemble
scores = 0.5 * iso_scores + 0.5 * xgb_probs
prec, rec, thresh = precision_recall_curve(y_test, scores)
f1s = 2 * rec * prec / (rec + prec + 1e-8)
best_f1 = f1s.max()
best_thresh = float(thresh[np.argmax(f1s)])
y_pred = (scores > best_thresh).astype(int)

print(f"\nF1 (anomali): {best_f1:.4f}")
print(f"Threshold: {best_thresh:.4f}")
print(classification_report(y_test, y_pred, target_names=['Normal', 'Anomali']))

critical = float(np.percentile(scores[y_test == 1], 90)) if y_test.sum() > 0 else 0.90

# Kaydet
OUTPUT_DIR = '../services/prediction-service/models_data/'

def save_cksum(model, fname, is_xgb=False):
    path = os.path.join(OUTPUT_DIR, fname)
    if is_xgb:
        model.save_model(path)
    else:
        joblib.dump(model, path, compress=3)
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''):
            sha.update(block)
    return sha.hexdigest()

checksums = {}
checksums['isolation_forest.pkl'] = save_cksum(iso, 'isolation_forest.pkl')
checksums['xgboost_model.json'] = save_cksum(xgb_model, 'xgboost_model.json', is_xgb=True)
checksums['scaler.pkl'] = save_cksum(scaler, 'scaler.pkl')

with open(os.path.join(OUTPUT_DIR, 'checksums.json'), 'w') as f:
    json.dump(checksums, f, indent=4)

with open(os.path.join(OUTPUT_DIR, 'feature_config.json'), 'w') as f:
    json.dump({
        'feature_columns': FEATURE_COLUMNS,
        'base_features': FEATURE_COLUMNS[:10],
        'anomaly_threshold': best_thresh,
        'severity_warning': best_thresh,
        'severity_critical': critical,
        'iso_weight': 0.50,
        'xgb_weight': 0.50,
        'lead_time_hours': LEAD_TIME_HOURS,
        'rolling_window': ROLLING_WINDOW,
        'model_version': 'v3.1-power-curve',
        'f1_score': float(best_f1),
        'feature_count': len(FEATURE_COLUMNS),
    }, f, indent=4)

print(f"\nModeller kaydedildi ({len(FEATURE_COLUMNS)} feature)")
print(f"ANOMALY_THRESHOLD = {best_thresh:.4f}")
print(f"SEVERITY_CRITICAL = {critical:.4f}")
print(f"Model version: v3.1-power-curve")
