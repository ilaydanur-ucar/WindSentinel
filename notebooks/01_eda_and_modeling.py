# %% [markdown]
# # Wind Sentinel - Early Fault Detection: EDA & Model Kurulumu
# Bu notebook'ta, ham SCADA verisinden Feature çıkarımı yapacak, ardından 
# Isolation Forest ve XGBoost modellerimizi eğitip dışa aktaracağız (.pkl).

# %%
import pandas as pd
import numpy as np
import joblib
import os
import hashlib
import json
# import matplotlib.pyplot as plt
# import seaborn as sns

from sklearn.ensemble import IsolationForest
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_curve

# Uyarıları kapatalım
import warnings
warnings.filterwarnings('ignore')

# Proje bazlı feature order'ı buradan alabiliriz (veya elle senkron tutarız)
# FEATURE_COLUMNS sırası KRİTİKTİR.
FEATURE_COLUMNS = [
    "wind_speed",
    "active_power",
    "wind_direction",
    "theoretical_power_curve",
    "wind_speed_rolling_mean",
    "wind_speed_rolling_std",
    "power_error"
]

# %% [markdown]
# ## 1. Veriyi Yükleme ve İnceleme
# SCADA verisetinizin yolu: `data/raw/Wind Farm A/datasets/0.csv`

# %%
DATA_PATH = '../data/raw/Wind Farm A/datasets/0.csv' 

try:
    # Veri ; ile ayrılmış
    df_raw = pd.read_csv(DATA_PATH, sep=';')
    print(f"Veri başarıyla yüklendi! Satır sayısı: {len(df_raw)}")
    
    # Gerekli kolonları seç ve isimlendir
    # Mapping based on feature_description.csv
    mapping = {
        'time_stamp': 'timestamp',
        'wind_speed_3_avg': 'wind_speed',
        'power_30_avg': 'active_power',
        'sensor_1_avg': 'wind_direction',
        'power_29_avg': 'theoretical_power_curve'
    }
    
    df = df_raw[list(mapping.keys())].rename(columns=mapping)
    display(df.head())
    
except Exception as e:
    print(f"HATA: Veri yüklenirken sorun oluştu: {e}")
    # Fallback: Dummy Data
    dates = pd.date_range(start='2024-01-01', periods=2000, freq='10min')
    df = pd.DataFrame({
        'timestamp': dates,
        'active_power': np.random.normal(500, 100, 2000),
        'wind_speed': np.random.normal(10, 2, 2000),
        'theoretical_power_curve': np.random.normal(510, 100, 2000),
        'wind_direction': np.random.uniform(0, 360, 2000)
    })
    print("Test için rastgele (Dummy) veriseti oluşturuldu.")

# %% [markdown]
# ## 2. Feature Engineering (Özellik Çıkarımı)

# %%
# Tarih formatını ayarla ve zaman serisi düzeni için sırala
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# 1. Hareketli Ortalamalar (Rolling Features) - Son 1 saat (6 ölçüm)
df['wind_speed_rolling_mean'] = df['wind_speed'].rolling(window=6, min_periods=1).mean()
df['wind_speed_rolling_std'] = df['wind_speed'].rolling(window=6, min_periods=1).std().fillna(0)

# 2. Üretim Hatası (Power Error)
df['power_error'] = df['theoretical_power_curve'] - df['active_power']

# Final X matrix
X = df[FEATURE_COLUMNS].copy()

print("Özellik çıkarımı tamamlandı. X matrisi şekli:", X.shape)

# %% [markdown]
# ## 3. Target Label Oluşturma (Simülasyon)
# Gözetimli öğrenme için "Anomali" etiketini (Y) güç hatasına göre otomatik oluşturalım.

# %%
# Teorik üretim 0'dan büyükse ve Aktif güç beklenen gücün %30 altındaysa anomali (1) diyelim.
df['is_anomaly'] = ((df['theoretical_power_curve'] > 0) & 
                    (df['power_error'] / (df['theoretical_power_curve'] + 1e-6) > 0.30)).astype(int)

y = df['is_anomaly']
print("Anomali Dağılımı:")
print(y.value_counts(normalize=True))

# %% [markdown]
# ## 4. Model Eğitim Süreci (Isolation Forest + XGBoost)

# %%
# Zaman serisi ayrımı (Shuffle=False)
split_idx = int(len(df) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

# --- Model 1: Isolation Forest ---
iso_forest = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
iso_forest.fit(X_train)

# Skor Normalizasyonu (Sigmoid)
def get_iso_normalized(model, data):
    raw_scores = model.decision_function(data) # Negatif = Anomali
    # Sigmoid dönüşümü: 1 / (1 + exp(raw)). 
    # IF'te raw_score ne kadar küçükse anomali o kadar olasıdır.
    # Bu dönüşümle yüksek değer = yüksek anomali olasılığı olur.
    return 1 / (1 + np.exp(raw_scores))

iso_test_scores = get_iso_normalized(iso_forest, X_test)

# --- Model 2: XGBoost ---
xgb_model = xgb.XGBClassifier(n_estimators=100, max_depth=5, random_state=42, eval_metric='logloss')
xgb_model.fit(X_train, y_train)

# Olasılık (Probability) üretme
xgb_test_probs = xgb_model.predict_proba(X_test)[:, 1]

# %% [markdown]
# ## 5. Ensemble & Optimal Threshold Hesaplama

# %%
# Hibrit Skor: 0.6 * Iso + 0.4 * XGB
hybrid_scores = (0.6 * iso_test_scores) + (0.4 * xgb_test_probs)

# Precision-Recall Curve ile en iyi eşiği bulma
precision, recall, thresholds = precision_recall_curve(y_test, hybrid_scores)
f1_scores = 2 * recall * precision / (recall + precision + 1e-8)
best_idx = np.argmax(f1_scores)
optimal_threshold = thresholds[best_idx]

# print(f"Hesaplanan Optimal Threshold: {optimal_threshold:.4f}")
# print(f"Eşik {optimal_threshold:.2f} için Max F1-Score: {f1_scores[best_idx]:.4f}")

# %% [markdown]
# ## 6. Modelleri ve Checksumları Kaydetme

# %%
OUTPUT_DIR = 'services/prediction-service/models_data/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_with_checksum(model, filename, is_xgb=False):
    path = os.path.join(OUTPUT_DIR, filename)
    if is_xgb:
        model.save_model(path) # XGBoost Native JSON format
    else:
        joblib.dump(model, path)
    
    # SHA256 Hash hesapla
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

checksums = {}
checksums['isolation_forest.pkl'] = save_with_checksum(iso_forest, 'isolation_forest.pkl')
# XGBoost'u .json olarak kaydediyoruz (Versiyon uyuşmazlığını çözmek için)
checksums['xgboost_model.json'] = save_with_checksum(xgb_model, 'xgboost_model.json', is_xgb=True)

with open(os.path.join(OUTPUT_DIR, 'checksums.json'), 'w') as f:
    json.dump(checksums, f, indent=4)

print(f"Modeller ve checksumlar kaydedildi. Optimal Threshold: {optimal_threshold}")
print("Lütfen bu eşiği app/core/feature_columns.py içine yazın.")
