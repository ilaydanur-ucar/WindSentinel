# ────────────────────────────────────────────────────────────
# feature_engineer.py — Özellik Türetme (İş Mantığı/Core)
# ────────────────────────────────────────────────────────────
#
# STATELLES YAKLAŞIM (Kullanıcı İsteği):
#   Bu sınıf tamamen durumsuzdur (Stateless). Kayan pencere 
#   (Rolling window) veya hafıza (memory state) KULLANMAZ. 
#   Her bir ölçüm satırı, dış dünyadan bağımsız olarak kendi
#   içerisindeki metriklerle yeni özelliklere (feature) dönüştürülür.
#
# SRP ve SAF FONKSİYONLAR:
#   Yan etki (side-effect) içermez. Sadece girdiyi alır (`RawMeasurementMessage`)
#   ve tamamen yeni bir çıktıyı (`FeatureMessage`) döndürür. Unit test 
#   yazması %100 kolaylaştırılmıştır.
# ────────────────────────────────────────────────────────────

from app.schemas import RawMeasurementMessage, FeatureMessage
from app.logger import logger


class FeatureEngineer:
    """
    Rüzgar türbini ham sensör verilerinden Makine Öğrenimi (Isolation Forest)
    için anlamlı metrikler üreten servis.
    """

    @staticmethod
    def process(raw_msg: RawMeasurementMessage) -> FeatureMessage:
        """
        Ham veriyi işleyip zenginleştirilmiş FeatureMessage döndürür.
        
        Sıfıra bölme (ZeroDivisionError) risklerine karşı güvenli (Safe) 
        matematiksel hesaplamalar barındırır.
        """
        try:
            # 1. Power Factor (Güç Çarpanı)
            # Formül: Aktif Güç / Kök((Aktif Güç^2) + (Reaktif Güçlerin Farkı^2))
            # Basitleştirilmiş oran tahmini için Aktif / (İndüktif + Kapasitif + 1)
            reactive_total = raw_msg.reactive_power_inductive + raw_msg.reactive_power_capacitive
            power_factor = (
                raw_msg.total_active_power / reactive_total 
                if reactive_total > 0 else 0.0
            )

            # 2. RPM Oranı (Jeneratör vs Rotor)
            # Rotor ve Jeneratör dönüş hızları arasındaki aktarım bütünlüğü
            rpm_ratio = (
                raw_msg.generator_rpm / raw_msg.rotor_rpm 
                if raw_msg.rotor_rpm > 0 else 0.0
            )

            # 3. Reactive Power Balance (Reaktif Güç Dengesi)
            # İndüktif ve Kapasitif reaktif güç arasındaki fark (Trafodaki stres)
            reactive_balance = raw_msg.reactive_power_inductive - raw_msg.reactive_power_capacitive

            # 4. Power to Wind Ratio (Rüzgar Hızına Göre Güç Verimliliği)
            # Üretilen anlık gücün, anlık rüzgar hızına oranı
            wind_ratio = (
                raw_msg.power_output / raw_msg.wind_speed 
                if raw_msg.wind_speed > 0 else 0.0
            )

            # Sonuç Şemasını (FeatureMessage) Oluştur
            # Pydantic, tip ve doğrulama güvenliklerini burada garanti eder.
            feature_msg = FeatureMessage(
                # Metadatalar (Doğrudan Kopyala)
                timestamp=raw_msg.timestamp,
                asset_id=raw_msg.asset_id,
                turbine_id=raw_msg.turbine_id,
                status_type_id=raw_msg.status_type_id,
                
                # Temel Sensörler (Doğrudan Kopyala)
                wind_speed=raw_msg.wind_speed,
                power_output=raw_msg.power_output,
                generator_rpm=raw_msg.generator_rpm,
                total_active_power=raw_msg.total_active_power,
                reactive_power_inductive=raw_msg.reactive_power_inductive,
                reactive_power_capacitive=raw_msg.reactive_power_capacitive,
                
                # YENİ TÜRETİLEN ÖZELLİKLER (Features)
                power_factor=round(power_factor, 4),
                rpm_ratio=round(rpm_ratio, 4),
                reactive_power_balance=round(reactive_balance, 4),
                power_to_wind_ratio=round(wind_ratio, 4),
            )

            return feature_msg

        except Exception as e:
            # İş mantığı sırasında oluşacak beklenmeyen matematik hatalarında log at
            logger.error(f"Feature Engineering başarısız: {e} - Veri: {raw_msg.model_dump_json()}")
            raise e
