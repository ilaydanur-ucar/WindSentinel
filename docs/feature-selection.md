# WindSentinel - SCADA Veri Analizi ve Feature Seçimi

## Veri Seti Özeti

- **Kaynak**: Wind Farm A (SCADA verileri)
- **Türbin Sayısı**: 5 adet (asset_id: 0, 10, 11, 13, 21)
- **Toplam Kayıt**: ~1.2 milyon satır
- **Zaman Aralığı**: 10 dakikalık periyotlarla ölçüm
- **Toplam Sensör**: 54 farklı sensör (81 kolon — avg/max/min/std varyantları dahil)
- **Normal Kayıt**: 898,672 (%75)
- **Anomali Kayıt**: 298,075 (%25)

## Tespit Edilen Arıza Tipleri

| Arıza Tipi                  | Sayı | Etkilenen Türbinler |
|-----------------------------|------|---------------------|
| Hydraulic group             | 5    | T00, T10, T13, T21  |
| Generator bearing failure   | 2    | T00, T10             |
| Gearbox failure             | 2    | T10, T21             |
| Gearbox bearings damaged    | 1    | T21                  |
| Transformer failure         | 1    | T11                  |

## Feature Seçim Metodolojisi

54 sensör (81 kolon) arasından en önemli feature'ları seçmek için **5 farklı yöntem** kullanıldı:

| # | Yöntem | Yaklaşım |
|---|--------|----------|
| 1 | **ANOVA F-Test** | İstatistiksel: Normal vs anomali grupları arasındaki varyans farkı |
| 2 | **Mutual Information** | Bilgi teorisi: Feature ile hedef arasındaki bağımlılık (lineer olmayan ilişkileri de yakalar) |
| 3 | **Random Forest Importance** | Ağaç bazlı: Her feature'ın karar vermeye katkısı |
| 4 | **Gradient Boosting Importance** | Güçlendirilmiş ağaç: Ardışık öğrenme ile feature katkısı |
| 5 | **Spearman Korelasyon** | İstatistiksel: Feature ile anomali etiketi arasındaki monoton ilişki |

### Konsensüs Sıralaması

5 yöntemin ortalama sıralamasına göre birleşik sonuç:

| Sıra | Feature | Açıklama | Top 10'da Görünme |
|------|---------|----------|-------------------|
| 1 | power_30_avg | Şebeke gücü (kW) | **5/5** |
| 2 | sensor_50 | Toplam aktif güç (Wh) | **5/5** |
| 3 | reactive_power_28_avg | İndüktif reaktif güç (kVAr) | 4/5 |
| 4 | sensor_18_avg | Jeneratör RPM | 4/5 |
| 5 | reactive_power_27_avg | Kapasitif reaktif güç (kVAr) | 4/5 |
| 6 | wind_speed_3_avg | Rüzgar hızı (m/s) | 3/5 |

## Seçilen 6 Temel Feature

### 1. power_30_avg — Şebeke Gücü (kW) — Konsensüs: 5/5
- **Neden**: Türbinin şebekeye verdiği gerçek güç çıktısı. Tüm yöntemler tarafından en önemli bulunan feature.
- **Anomali ilişkisi**: Rüzgar hızına göre beklenen güç ile gerçek güç arasındaki sapma, arızanın en güvenilir göstergesi.
- **Gradient Boosting'de tek başına %50 importance taşıyor.**

### 2. sensor_50 — Toplam Aktif Güç (Wh) — Konsensüs: 5/5
- **Neden**: Kümülatif enerji üretimi. Anlık güçten farklı olarak uzun vadeli üretim trendini gösterir.
- **Anomali ilişkisi**: Üretim düşüşleri veya anormal artışlar, mekanik/elektriksel sorunlara işaret eder.

### 3. reactive_power_28_avg — İndüktif Reaktif Güç (kVAr) — Konsensüs: 4/5
- **Neden**: Şebeke ile türbin arasındaki elektriksel dengenin göstergesi.
- **Anomali ilişkisi**: Reaktif güç sapmaları, jeneratör veya trafo arızalarının habercisi.

### 4. sensor_18_avg — Jeneratör RPM (rpm) — Konsensüs: 4/5
- **Neden**: Jeneratör dönüş hızı, bearing arızaları ve elektriksel sorunların doğrudan göstergesi.
- **Anomali ilişkisi**: RPM dalgalanmaları veya beklenmeyen düşüşler → jeneratör bearing failure.

### 5. reactive_power_27_avg — Kapasitif Reaktif Güç (kVAr) — Konsensüs: 4/5
- **Neden**: Şebeke kapasitif reaktif güç kapasitesi. Elektriksel stabilite göstergesi.
- **Anomali ilişkisi**: Kapasitif-indüktif güç dengesizliği → şebeke bağlantı sorunları.

### 6. wind_speed_3_avg — Rüzgar Hızı (m/s) — Konsensüs: 3/5
- **Neden**: Konsensüste 3/5 olmasına rağmen, diğer feature'larla birlikte çalıştığında F1 skorunu %82'den %88'e çıkarıyor. Tek başına anomaliyi ayırt etmez ama diğer feature'ların REFERANS noktasıdır.
- **Anomali ilişkisi**: "Bu rüzgar hızında bu güç/RPM normal mi?" sorusunun cevabı ancak rüzgar hızı bilinince verilebilir.

## Performans Karşılaştırması

| Feature Seti | F1 Skoru | Not |
|---|---|---|
| **Seçilen 6 feature** | **0.8836** | En verimli set |
| Eski 5 feature (sezgisel) | 0.8834 | Benzer performans |
| Konsensüs 5 (rüzgar hızısız) | 0.8214 | Rüzgar hızı olmadan düşüyor |
| Tüm 81 feature | 0.8855 | Sadece %0.2 fark |

**Sonuç**: 6 feature ile 81 feature arasında sadece %0.2 fark var. 6 feature seçimi hem hesaplama maliyetini düşürür hem de modelin yorumlanabilirliğini artırır.

## Türetilecek Ek Feature'lar (Feature Engineering)

| Feature | Formül | Açıklama |
|---------|--------|----------|
| power_ratio | power_30_avg / sensor_50 | Anlık güç / toplam güç oranı |
| reactive_balance | reactive_power_27 / reactive_power_28 | Kapasitif/İndüktif güç dengesi |
| power_per_wind | power_30_avg / wind_speed_3_avg | Rüzgar başına güç (verimlilik) |
| rolling_avg_power | power_30 son 6 periyot ortalaması | Güç trendi |
| rolling_std_rpm | sensor_18 son 6 periyot std | RPM kararsızlığı |
