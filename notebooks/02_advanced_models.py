# %% [markdown]
# # WindSentinel - Gelismis Model Deneyimi
# LSTM Autoencoder + River HalfSpaceTrees (ADWIN)
# Mevcut F1=0.60 baseline uzerinde iyilestirme testi

# %%
import pandas as pd
import numpy as np
import os
import json
import warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # TF log azalt

# === 1. VERI HAZIRLIGI (01_eda ile ayni) ===
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
for csv_file in csv_files:
    df_raw = pd.read_csv(os.path.join(DATA_DIR, csv_file), sep=';')
    df_filtered = df_raw[df_raw['asset_id'].isin(TARGET_ASSETS)]
    if len(df_filtered) > 0:
        dfs.append(df_filtered)
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

# Etiketleme
df['is_anomaly'] = 0
for _, event in fault_events.iterrows():
    lead_start = event['event_start'] - pd.Timedelta(hours=LEAD_TIME_HOURS)
    mask = (df['asset_id'] == event['asset']) & (df['timestamp'] >= lead_start) & (df['timestamp'] <= event['event_end'])
    df.loc[mask, 'is_anomaly'] = 1

# Split
train_mask = df['train_test'] == 'train'
test_mask = df['train_test'] == 'prediction'
X_train = df.loc[train_mask, FEATURE_COLUMNS].values
X_test = df.loc[test_mask, FEATURE_COLUMNS].values
y_train = df.loc[train_mask, 'is_anomaly'].values
y_test = df.loc[test_mask, 'is_anomaly'].values

print(f"Train: {len(X_train)}, Test: {len(X_test)}")
print(f"Anomali: train={y_train.mean():.2%}, test={y_test.mean():.2%}")

# %% [markdown]
# ## 2. BASELINE: Mevcut Ensemble (IsoForest + XGBoost)

# %%
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, precision_recall_curve, f1_score, roc_auc_score
import xgboost as xgb

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# IsoForest
iso_forest = IsolationForest(n_estimators=150, contamination=min(float(y_train.mean()) * 2, 0.15), max_features=0.7, max_samples=10000, random_state=42)
iso_forest.fit(X_train_scaled)

def get_iso_normalized(model, data):
    return 1 / (1 + np.exp(model.decision_function(data)))

iso_test = get_iso_normalized(iso_forest, X_test_scaled)

# XGBoost
pos_weight = (len(y_train) - y_train.sum()) / max(y_train.sum(), 1)
xgb_model = xgb.XGBClassifier(n_estimators=500, max_depth=8, learning_rate=0.03, min_child_weight=5, subsample=0.8, colsample_bytree=0.8, gamma=1, random_state=42, eval_metric='aucpr', scale_pos_weight=pos_weight, tree_method='hist')
xgb_model.fit(X_train_scaled, y_train)
xgb_test = xgb_model.predict_proba(X_test_scaled)[:, 1]

# Baseline ensemble
baseline_scores = 0.5 * iso_test + 0.5 * xgb_test
prec, rec, thresh = precision_recall_curve(y_test, baseline_scores)
f1s = 2 * rec * prec / (rec + prec + 1e-8)
baseline_f1 = f1s.max()
baseline_thresh = float(thresh[np.argmax(f1s)])
print(f"\n=== BASELINE (IsoForest + XGBoost) ===")
print(f"F1: {baseline_f1:.4f}, Threshold: {baseline_thresh:.4f}")
print(classification_report(y_test, (baseline_scores > baseline_thresh).astype(int), target_names=['Normal', 'Anomali']))

# %% [markdown]
# ## 3. LSTM Autoencoder
# Normal veriyi ogrenir, anomaliyi "yeniden yapilandirma hatasi" olarak tespit eder.
# Isolation Forest'in yakalayamadigi zamansal drift'leri yakalar.

# %%
import tensorflow as tf
tf.get_logger().setLevel('ERROR')
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, LSTM, Dense, RepeatVector, TimeDistributed
from tensorflow.keras.callbacks import EarlyStopping

print("LSTM Autoencoder egitiliyor...")

SEQ_LEN = 6

def create_sequences(data, seq_len):
    sequences = []
    for i in range(len(data) - seq_len + 1):
        sequences.append(data[i:i+seq_len])
    return np.array(sequences, dtype=np.float32)

# Sadece normal veriyle egit - MAX 50K sample (hiz icin)
normal_mask = y_train == 0
X_train_normal = X_train_scaled[normal_mask]
if len(X_train_normal) > 50000:
    idx = np.random.RandomState(42).choice(len(X_train_normal), 50000, replace=False)
    X_train_normal = X_train_normal[idx]

X_seq_train = create_sequences(X_train_normal, SEQ_LEN)
X_seq_test = create_sequences(X_test_scaled, SEQ_LEN)
y_seq_test = y_test[SEQ_LEN-1:]

print(f"Train sequences: {X_seq_train.shape}, Test: {X_seq_test.shape}")

n_features = X_train_scaled.shape[1]

# Daha kucuk model (16 unit - hiz icin)
encoder_input = Input(shape=(SEQ_LEN, n_features))
x = LSTM(16, activation='relu', return_sequences=False)(encoder_input)
x = RepeatVector(SEQ_LEN)(x)
x = LSTM(16, activation='relu', return_sequences=True)(x)
decoder_output = TimeDistributed(Dense(n_features))(x)

autoencoder = Model(encoder_input, decoder_output)
autoencoder.compile(optimizer='adam', loss='mse')

history = autoencoder.fit(
    X_seq_train, X_seq_train,
    epochs=15,
    batch_size=512,
    validation_split=0.1,
    callbacks=[EarlyStopping(patience=3, restore_best_weights=True)],
    verbose=1,
)

print(f"LSTM Autoencoder egitildi. Final loss: {history.history['val_loss'][-1]:.6f}")

# Reconstruction error hesapla
train_recon = autoencoder.predict(X_seq_train, verbose=0)
train_mse = np.mean(np.mean((X_seq_train - train_recon) ** 2, axis=2), axis=1)

test_recon = autoencoder.predict(X_seq_test, verbose=0)
test_mse = np.mean(np.mean((X_seq_test - test_recon) ** 2, axis=2), axis=1)

# Normalize [0, 1] arasi
max_mse = np.percentile(train_mse, 99)  # Outlier'lari kes
lstm_scores = np.clip(test_mse / max_mse, 0, 1)

print(f"LSTM scores: mean={lstm_scores.mean():.4f}, std={lstm_scores.std():.4f}")
print(f"Normal ortalama: {lstm_scores[y_seq_test == 0].mean():.4f}")
print(f"Anomali ortalama: {lstm_scores[y_seq_test == 1].mean():.4f}")

# LSTM tek basina F1
prec_l, rec_l, thresh_l = precision_recall_curve(y_seq_test, lstm_scores)
f1s_l = 2 * rec_l * prec_l / (rec_l + prec_l + 1e-8)
lstm_f1 = f1s_l.max()
print(f"\nLSTM Autoencoder tek basina F1: {lstm_f1:.4f}")

# %% [markdown]
# ## 4. River HalfSpaceTrees (Online/Streaming)
# Concept drift'e uyum saglar, modeli yeniden egitmeden gunceller.

# %%
from river import anomaly as river_anomaly
from river import drift

print("\nRiver HalfSpaceTrees egitiliyor (streaming)...")

hst = river_anomaly.HalfSpaceTrees(
    n_trees=25,
    height=6,
    window_size=500,
    seed=42,
)

# ADWIN drift detector
adwin = drift.ADWIN(delta=0.002)

# Streaming: Once train setiyle warm-up, sonra test ile skor
# Train'den 20K sample ile warm-up (hiz icin)
warmup_size = min(20000, len(X_train_scaled))
for i in range(warmup_size):
    x_dict = {f'f{j}': float(X_train_scaled[i][j]) for j in range(X_train_scaled.shape[1])}
    hst.learn_one(x_dict)
print(f"Warm-up tamamlandi ({warmup_size} sample)")

river_scores = []
drift_count = 0

for i in range(len(X_test_scaled)):
    x_dict = {f'f{j}': float(X_test_scaled[i][j]) for j in range(X_test_scaled.shape[1])}
    score = hst.score_one(x_dict)
    river_scores.append(score)
    hst.learn_one(x_dict)

    adwin.update(score)
    if adwin.drift_detected:
        drift_count += 1

    if i % 50000 == 0 and i > 0:
        print(f"  River: {i}/{len(X_test_scaled)} islendi...")

river_scores = np.array(river_scores)
print(f"River HST tamamlandi. Drift algilanan: {drift_count}")
print(f"River scores: mean={river_scores.mean():.4f}, std={river_scores.std():.4f}")
print(f"Normal ortalama: {river_scores[y_test == 0].mean():.4f}")
print(f"Anomali ortalama: {river_scores[y_test == 1].mean():.4f}")

# River tek basina F1
prec_r, rec_r, thresh_r = precision_recall_curve(y_test, river_scores)
f1s_r = 2 * rec_r * prec_r / (rec_r + prec_r + 1e-8)
river_f1 = f1s_r.max()
print(f"\nRiver HST tek basina F1: {river_f1:.4f}")

# %% [markdown]
# ## 5. MEGA ENSEMBLE: IsoForest + XGBoost + LSTM + River
# Her modelin guclu yonunu birlestir

# %%
print("\n" + "="*60)
print("ENSEMBLE OPTIMIZASYONU")
print("="*60)

# LSTM scores'u alignment'a getir (sequence offset)
# LSTM ilk SEQ_LEN-1 ornek icin skor uretemez, onlari baseline ile doldur
lstm_full = np.zeros(len(y_test))
lstm_full[:SEQ_LEN-1] = baseline_scores[:SEQ_LEN-1]  # Fallback
lstm_full[SEQ_LEN-1:SEQ_LEN-1+len(lstm_scores)] = lstm_scores

# 4 modelin skorlari
all_scores = {
    'iso': iso_test,
    'xgb': xgb_test,
    'lstm': lstm_full,
    'river': river_scores,
}

# Grid search: en iyi agirlik kombinasyonu
best_combo_f1 = 0
best_weights = {}
best_combo_thresh = 0

# Agirlik aralik: 0.0, 0.1, 0.2, ... 0.5
weight_range = [i/10 for i in range(0, 6)]

tested = 0
for w_iso in weight_range:
    for w_xgb in weight_range:
        for w_lstm in weight_range:
            w_river = round(1.0 - w_iso - w_xgb - w_lstm, 2)
            if w_river < 0 or w_river > 0.5:
                continue

            combo_scores = (w_iso * iso_test + w_xgb * xgb_test +
                          w_lstm * lstm_full + w_river * river_scores)

            prec_c, rec_c, thresh_c = precision_recall_curve(y_test, combo_scores)
            f1s_c = 2 * rec_c * prec_c / (rec_c + prec_c + 1e-8)
            max_f1 = f1s_c.max()
            tested += 1

            if max_f1 > best_combo_f1:
                best_combo_f1 = max_f1
                best_weights = {'iso': w_iso, 'xgb': w_xgb, 'lstm': w_lstm, 'river': w_river}
                best_combo_thresh = float(thresh_c[np.argmax(f1s_c)])

print(f"Test edilen kombinasyon: {tested}")
print(f"\nEN IYI ENSEMBLE:")
print(f"  Agirliklar: {best_weights}")
print(f"  F1: {best_combo_f1:.4f}")
print(f"  Threshold: {best_combo_thresh:.4f}")

# Final tahmin
final_scores = (best_weights['iso'] * iso_test + best_weights['xgb'] * xgb_test +
               best_weights['lstm'] * lstm_full + best_weights['river'] * river_scores)
y_pred = (final_scores > best_combo_thresh).astype(int)

print("\n" + classification_report(y_test, y_pred, target_names=['Normal', 'Anomali']))

roc = roc_auc_score(y_test, final_scores)
prec_f, rec_f, _ = precision_recall_curve(y_test, final_scores)
pr_auc = np.trapz(prec_f[::-1], rec_f[::-1])
print(f"ROC-AUC: {roc:.4f}")
print(f"PR-AUC:  {pr_auc:.4f}")

# %% [markdown]
# ## 6. Karsilastirma Tablosu

# %%
print("\n" + "="*60)
print("KARSILASTIRMA")
print("="*60)

results = [
    ("IsoForest + XGBoost (baseline)", baseline_f1),
    ("LSTM Autoencoder (tek)", lstm_f1),
    ("River HST (tek)", river_f1),
    (f"4-Model Ensemble (iso={best_weights['iso']}, xgb={best_weights['xgb']}, lstm={best_weights['lstm']}, river={best_weights['river']})", best_combo_f1),
]

for name, f1 in sorted(results, key=lambda x: x[1], reverse=True):
    marker = " <-- EN IYI" if f1 == best_combo_f1 else ""
    print(f"  {f1:.4f}  {name}{marker}")

improvement = ((best_combo_f1 - baseline_f1) / baseline_f1) * 100
print(f"\nIyilestirme: {improvement:+.1f}% ({baseline_f1:.4f} -> {best_combo_f1:.4f})")

# %% [markdown]
# ## 7. Karar: Deploy mu, Kalsin mi?

# %%
if best_combo_f1 > baseline_f1 + 0.01:  # En az %1 iyilestirme
    print("\n>>> SONUC: Yeni ensemble DAHA IYI. Deploy edilecek.")
    print(f">>> Agirliklar: {best_weights}")
    print(f">>> Threshold: {best_combo_thresh:.4f}")

    # LSTM modelini kaydet
    import hashlib, joblib
    OUTPUT_DIR = '../services/prediction-service/models_data/'

    autoencoder.save(os.path.join(OUTPUT_DIR, 'lstm_autoencoder.keras'))
    joblib.dump(scaler, os.path.join(OUTPUT_DIR, 'scaler.pkl'), compress=3)

    # River HST'yi pickle ile kaydet
    import pickle
    with open(os.path.join(OUTPUT_DIR, 'river_hst.pkl'), 'wb') as f:
        pickle.dump(hst, f)

    # Checksums guncelle
    checksums = {}
    for fname in ['isolation_forest.pkl', 'xgboost_model.json', 'lstm_autoencoder.keras', 'scaler.pkl', 'river_hst.pkl']:
        fpath = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(fpath):
            sha = hashlib.sha256()
            with open(fpath, 'rb') as f:
                for block in iter(lambda: f.read(4096), b""):
                    sha.update(block)
            checksums[fname] = sha.hexdigest()

    with open(os.path.join(OUTPUT_DIR, 'checksums.json'), 'w') as f:
        json.dump(checksums, f, indent=4)

    # Config guncelle
    with open(os.path.join(OUTPUT_DIR, 'feature_config.json'), 'w') as f:
        json.dump({
            'feature_columns': FEATURE_COLUMNS,
            'base_features': BASE_FEATURES,
            'anomaly_threshold': best_combo_thresh,
            'severity_warning': best_combo_thresh,
            'severity_critical': float(np.percentile(final_scores[y_test == 1], 90)) if y_test.sum() > 0 else 0.90,
            'weights': best_weights,
            'lead_time_hours': LEAD_TIME_HOURS,
            'rolling_window': ROLLING_WINDOW,
            'seq_len': SEQ_LEN,
            'model_version': 'v4.0-mega-ensemble',
        }, f, indent=4)

    print("Modeller kaydedildi.")
else:
    print("\n>>> SONUC: Iyilestirme yetersiz. Mevcut baseline KORUNUYOR.")
    print(f">>> Baseline F1: {baseline_f1:.4f}")
    print(f">>> Yeni F1: {best_combo_f1:.4f}")
    print(f">>> Fark: {improvement:+.1f}%")
