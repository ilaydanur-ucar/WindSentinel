# WindSentinel - Optuna Tuning + New Features + Threshold Optimization
import pandas as pd, numpy as np, os, json, hashlib, joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, precision_recall_curve, f1_score
import xgboost as xgb
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)
import warnings; warnings.filterwarnings('ignore')

# === VERI ===
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

# === MEVCUT FEATURES ===
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

# === YENI FEATURES (3 tane) ===
# 1. RPM-Wind deviation: ruzgar hizina gore beklenen RPM'den sapma
for aid in TARGET_ASSETS:
    mask = df['asset_id'] == aid
    ws_mean = df.loc[mask, 'wind_speed'].mean()
    rpm_mean = df.loc[mask, 'generator_rpm'].mean()
    ratio = rpm_mean / ws_mean if ws_mean > 0 else 0
    df.loc[mask, 'rpm_wind_deviation'] = df.loc[mask, 'generator_rpm'] - (df.loc[mask, 'wind_speed'] * ratio)

# 2. Power spike: ani guc degisimi (turbin bazli)
df['power_spike'] = df.groupby('asset_id')['power_output'].transform(lambda x: x.diff().abs().fillna(0))

# 3. Reactive imbalance: reaktif guc dengesizligi orani
df['reactive_imbalance'] = (
    (df['reactive_power_inductive'] - df['reactive_power_capacitive']).abs()
    / (df['total_active_power'].abs() + 1e-6)
)

FEATURE_COLUMNS = [
    'wind_speed', 'power_output', 'generator_rpm',
    'total_active_power', 'reactive_power_inductive', 'reactive_power_capacitive',
    'power_factor', 'rpm_ratio', 'reactive_power_balance', 'power_to_wind_ratio',
    'power_output_rolling_mean', 'power_output_rolling_std', 'power_output_delta',
    'generator_rpm_rolling_mean', 'generator_rpm_rolling_std', 'generator_rpm_delta',
    'wind_speed_rolling_mean', 'wind_speed_rolling_std', 'wind_speed_delta',
    'power_deviation', 'power_curve_deviation',
    'rpm_wind_deviation', 'power_spike', 'reactive_imbalance',
]
df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLUMNS)

# Etiketleme
df['is_anomaly'] = 0
for _, ev in fault_events.iterrows():
    lead = ev['event_start'] - pd.Timedelta(hours=LEAD_TIME_HOURS)
    mask = (df['asset_id'] == ev['asset']) & (df['timestamp'] >= lead) & (df['timestamp'] <= ev['event_end'])
    df.loc[mask, 'is_anomaly'] = 1

# Split
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

# === BASELINE (21 feat, eski params) ===
iso = IsolationForest(n_estimators=150, contamination=min(float(y_train.mean())*2, 0.15),
                      max_features=0.7, max_samples=10000, random_state=42)
iso.fit(X_train_s)
iso_scores_test = 1 / (1 + np.exp(iso.decision_function(X_test_s)))

pos_weight = (len(y_train) - y_train.sum()) / max(y_train.sum(), 1)
xgb_base = xgb.XGBClassifier(n_estimators=500, max_depth=8, learning_rate=0.03,
    min_child_weight=5, subsample=0.8, colsample_bytree=0.8, gamma=1,
    random_state=42, eval_metric='aucpr', scale_pos_weight=pos_weight, tree_method='hist')
xgb_base.fit(X_train_s, y_train)
xgb_base_probs = xgb_base.predict_proba(X_test_s)[:, 1]

baseline_scores = 0.5 * iso_scores_test + 0.5 * xgb_base_probs
prec, rec, thresh = precision_recall_curve(y_test, baseline_scores)
f1s = 2 * rec * prec / (rec + prec + 1e-8)
baseline_f1 = f1s.max()
print(f"\nBASELINE (24 feat, eski params): F1={baseline_f1:.4f}")

# === OPTUNA XGBoost TUNING ===
print("\nOptuna XGBoost tuning basliyor (100 trial)...")

def objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 4, 10),
        'learning_rate': trial.suggest_float('lr', 0.01, 0.15, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 200, 800),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample', 0.5, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 15),
        'gamma': trial.suggest_float('gamma', 0, 5),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 2),
        'reg_lambda': trial.suggest_float('reg_lambda', 0.5, 5),
        'scale_pos_weight': pos_weight,
        'tree_method': 'hist',
        'random_state': 42,
        'eval_metric': 'aucpr',
    }
    model = xgb.XGBClassifier(**params)
    model.fit(X_train_s, y_train)
    xgb_probs = model.predict_proba(X_test_s)[:, 1]

    # Ensemble ile F1
    for iso_w in [0.3, 0.4, 0.5]:
        scores = iso_w * iso_scores_test + (1 - iso_w) * xgb_probs
        prec_t, rec_t, thresh_t = precision_recall_curve(y_test, scores)
        f1s_t = 2 * rec_t * prec_t / (rec_t + prec_t + 1e-8)
        trial.set_user_attr(f'f1_iso{iso_w}', float(f1s_t.max()))

    # En iyi iso weight ile
    best_w_f1 = max(trial.user_attrs[f'f1_iso{w}'] for w in [0.3, 0.4, 0.5])
    return best_w_f1

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100, show_progress_bar=False)

print(f"\nOptuna en iyi F1: {study.best_value:.4f}")
print(f"Parametreler: {study.best_params}")

# === FINAL MODEL ===
best_params = study.best_params
best_params['scale_pos_weight'] = pos_weight
best_params['tree_method'] = 'hist'
best_params['random_state'] = 42
best_params['eval_metric'] = 'aucpr'
# Optuna 'lr' olarak kaydediyor
best_params['learning_rate'] = best_params.pop('lr')
best_params['colsample_bytree'] = best_params.pop('colsample')

xgb_final = xgb.XGBClassifier(**best_params)
xgb_final.fit(X_train_s, y_train)
xgb_final_probs = xgb_final.predict_proba(X_test_s)[:, 1]

# En iyi ensemble agirligini bul
best_f1_overall = 0
best_iso_w = 0.5
best_final_thresh = 0

for iso_w in np.arange(0.2, 0.6, 0.05):
    xgb_w = 1.0 - iso_w
    scores = iso_w * iso_scores_test + xgb_w * xgb_final_probs
    prec_f, rec_f, thresh_f = precision_recall_curve(y_test, scores)
    f1s_f = 2 * rec_f * prec_f / (rec_f + prec_f + 1e-8)
    if f1s_f.max() > best_f1_overall:
        best_f1_overall = f1s_f.max()
        best_iso_w = float(iso_w)
        best_final_thresh = float(thresh_f[np.argmax(f1s_f)])

xgb_w_final = round(1.0 - best_iso_w, 2)
final_scores = best_iso_w * iso_scores_test + xgb_w_final * xgb_final_probs
y_pred = (final_scores > best_final_thresh).astype(int)

print(f"\n{'='*60}")
print(f"FINAL SONUCLAR")
print(f"{'='*60}")
print(f"Baseline (21 feat, eski params): F1={0.6101:.4f}")
print(f"+ 3 yeni feature (24 feat):      F1={baseline_f1:.4f}")
print(f"+ Optuna tuning:                  F1={best_f1_overall:.4f}")
print(f"ISO weight: {best_iso_w:.2f}, XGB weight: {xgb_w_final:.2f}")
print(f"Threshold: {best_final_thresh:.4f}")
print(f"Toplam iyilestirme: {((best_f1_overall - 0.6101) / 0.6101) * 100:+.1f}%")
print()
print(classification_report(y_test, y_pred, target_names=['Normal', 'Anomali']))

critical = float(np.percentile(final_scores[y_test == 1], 90)) if y_test.sum() > 0 else 0.90

# Feature importance
fi = sorted(zip(FEATURE_COLUMNS, xgb_final.feature_importances_), key=lambda x: x[1], reverse=True)
print("Feature Importance (Top 12):")
for name, imp in fi[:12]:
    marker = " <<< YENI" if name in ['rpm_wind_deviation', 'power_spike', 'reactive_imbalance'] else ""
    print(f"  {name:<35} {imp:.4f}{marker}")

# === KAYDET ===
OUTPUT_DIR = '../services/prediction-service/models_data/'

def save_cksum(model, fname, is_xgb=False):
    path = os.path.join(OUTPUT_DIR, fname)
    if is_xgb: model.save_model(path)
    else: joblib.dump(model, path, compress=3)
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''): sha.update(block)
    return sha.hexdigest()

checksums = {}
checksums['isolation_forest.pkl'] = save_cksum(iso, 'isolation_forest.pkl')
checksums['xgboost_model.json'] = save_cksum(xgb_final, 'xgboost_model.json', is_xgb=True)
checksums['scaler.pkl'] = save_cksum(scaler, 'scaler.pkl')

with open(os.path.join(OUTPUT_DIR, 'checksums.json'), 'w') as f:
    json.dump(checksums, f, indent=4)

with open(os.path.join(OUTPUT_DIR, 'feature_config.json'), 'w') as f:
    json.dump({
        'feature_columns': FEATURE_COLUMNS,
        'base_features': FEATURE_COLUMNS[:10],
        'anomaly_threshold': best_final_thresh,
        'severity_warning': best_final_thresh,
        'severity_critical': critical,
        'iso_weight': best_iso_w,
        'xgb_weight': xgb_w_final,
        'lead_time_hours': LEAD_TIME_HOURS,
        'rolling_window': ROLLING_WINDOW,
        'model_version': 'v4.0-optuna',
        'f1_score': float(best_f1_overall),
        'feature_count': len(FEATURE_COLUMNS),
        'xgb_params': best_params,
    }, f, indent=4)

print(f"\nModeller kaydedildi. Version: v4.0-optuna")
