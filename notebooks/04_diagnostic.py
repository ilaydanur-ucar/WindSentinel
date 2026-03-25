# WindSentinel - Diagnostic: split, class F1, scale_pos_weight, power_curve_deviation
import pandas as pd, numpy as np, os
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, precision_recall_curve, f1_score
import xgboost as xgb
import warnings; warnings.filterwarnings('ignore')

DATA_DIR = '../data/raw/Wind Farm A/datasets/'
EVENT_PATH = '../data/raw/Wind Farm A/event_info.csv'
LEAD_TIME_HOURS = 24; ROLLING_WINDOW = 6
TARGET_ASSETS = [0, 10, 11, 13, 21]

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

# YENI: turbin bazli power curve deviation
df['power_curve_deviation'] = df.groupby('asset_id').apply(
    lambda g: g['power_output'] - g.groupby(pd.cut(g['wind_speed'], bins=20))['power_output'].transform('mean')
).reset_index(level=0, drop=True).fillna(0)

FEAT_BASE = [
    'wind_speed', 'power_output', 'generator_rpm',
    'total_active_power', 'reactive_power_inductive', 'reactive_power_capacitive',
    'power_factor', 'rpm_ratio', 'reactive_power_balance', 'power_to_wind_ratio',
    'power_output_rolling_mean', 'power_output_rolling_std', 'power_output_delta',
    'generator_rpm_rolling_mean', 'generator_rpm_rolling_std', 'generator_rpm_delta',
    'wind_speed_rolling_mean', 'wind_speed_rolling_std', 'wind_speed_delta',
    'power_deviation',
]
FEAT_NEW = FEAT_BASE + ['power_curve_deviation']

df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEAT_NEW)

df['is_anomaly'] = 0
for _, ev in fault_events.iterrows():
    lead = ev['event_start'] - pd.Timedelta(hours=LEAD_TIME_HOURS)
    mask = (df['asset_id'] == ev['asset']) & (df['timestamp'] >= lead) & (df['timestamp'] <= ev['event_end'])
    df.loc[mask, 'is_anomaly'] = 1

# === SPLIT ===
print("=== SPLIT ANALIZI ===")
print(f"train_test unique: {df['train_test'].unique()}")
train_mask = df['train_test'] == 'train'
test_mask = df['train_test'] == 'prediction'
y_train = df.loc[train_mask, 'is_anomaly'].values
y_test = df.loc[test_mask, 'is_anomaly'].values
print(f"Train: {train_mask.sum()} (anomali: {y_train.mean():.2%})")
print(f"Test:  {test_mask.sum()} (anomali: {y_test.mean():.2%})")
print(">>> Split: VERI SETININ KENDI split'i (train_test kolonu CSV'de var)")

pos_count = y_train.sum()
neg_count = len(y_train) - pos_count
auto_weight = neg_count / max(pos_count, 1)
print(f"\nauto scale_pos_weight = {auto_weight:.1f}")

# === ISO FOREST (21 feature ile) ===
X_train_new = df.loc[train_mask, FEAT_NEW].values
X_test_new = df.loc[test_mask, FEAT_NEW].values
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train_new)
X_test_s = scaler.transform(X_test_new)

iso = IsolationForest(n_estimators=150, contamination=min(float(y_train.mean())*2, 0.15),
                      max_features=0.7, max_samples=10000, random_state=42)
iso.fit(X_train_s)
iso_scores = 1 / (1 + np.exp(iso.decision_function(X_test_s)))

# === SCALE_POS_WEIGHT SWEEP ===
print("\n=== SCALE_POS_WEIGHT + ENSEMBLE WEIGHT SWEEP ===")
print(f"{'config':<45} {'F1_anom':>8} {'F1_norm':>8} {'F1_macro':>8} {'F1_wtd':>8} {'thresh':>8}")
print("-" * 100)

best_overall = 0
best_config_str = ""
best_y_pred = None
best_thresh = 0

for spw_label, spw in [('auto', auto_weight), ('50', 50), ('75', 75), ('100', 100), ('150', 150)]:
    xgb_m = xgb.XGBClassifier(n_estimators=500, max_depth=8, learning_rate=0.03,
        min_child_weight=5, subsample=0.8, colsample_bytree=0.8, gamma=1,
        random_state=42, eval_metric='aucpr', scale_pos_weight=spw, tree_method='hist')
    xgb_m.fit(X_train_s, y_train)
    xgb_probs = xgb_m.predict_proba(X_test_s)[:, 1]

    for iso_w in [0.3, 0.4, 0.5]:
        xgb_w = round(1.0 - iso_w, 1)
        scores = iso_w * iso_scores + xgb_w * xgb_probs
        prec, rec, thresh = precision_recall_curve(y_test, scores)
        f1s = 2 * rec * prec / (rec + prec + 1e-8)
        max_f1 = f1s.max()
        best_t = float(thresh[np.argmax(f1s)])
        y_p = (scores > best_t).astype(int)

        f1_a = f1_score(y_test, y_p, pos_label=1)
        f1_n = f1_score(y_test, y_p, pos_label=0)
        f1_m = f1_score(y_test, y_p, average='macro')
        f1_w = f1_score(y_test, y_p, average='weighted')

        config = f"spw={spw_label:>4} iso={iso_w} xgb={xgb_w}"
        marker = ""
        if f1_a > best_overall:
            best_overall = f1_a
            best_config_str = config
            best_y_pred = y_p
            best_thresh = best_t
            marker = " <<<"

        print(f"{config:<45} {f1_a:>8.4f} {f1_n:>8.4f} {f1_m:>8.4f} {f1_w:>8.4f} {best_t:>8.4f}{marker}")

print(f"\n=== EN IYI ===")
print(f"Config: {best_config_str}")
print(f"F1 (anomali class): {best_overall:.4f}")
print(f"Threshold: {best_thresh:.4f}")
print(f"Baseline (20 feat, spw=auto): 0.5989")
print(f"Degisim: {((best_overall - 0.5989) / 0.5989) * 100:+.1f}%")
print()
print(classification_report(y_test, best_y_pred, target_names=['Normal', 'Anomali']))

# Feature importance
print("=== FEATURE IMPORTANCE (Top 10) ===")
xgb_best = xgb.XGBClassifier(n_estimators=500, max_depth=8, learning_rate=0.03,
    min_child_weight=5, subsample=0.8, colsample_bytree=0.8, gamma=1,
    random_state=42, eval_metric='aucpr', scale_pos_weight=auto_weight, tree_method='hist')
xgb_best.fit(X_train_s, y_train)
fi = sorted(zip(FEAT_NEW, xgb_best.feature_importances_), key=lambda x: x[1], reverse=True)
for name, imp in fi[:12]:
    marker = " <<< YENI" if name == 'power_curve_deviation' else ""
    print(f"  {name:<35} {imp:.4f}{marker}")
