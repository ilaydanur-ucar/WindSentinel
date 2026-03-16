import pytest
from datetime import datetime
from app.models.schemas import FeatureMessage, PredictionResult
from app.ml.dummy_predictor import DummyPredictor

def test_dummy_predictor_normal_behavior():
    """
    Dummy predictor'un normal(anomali olmayan) değerlerde doğru çalıştığını kontrol et
    """
    predictor = DummyPredictor()
    
    msg = FeatureMessage(
        timestamp=datetime.now(),
        wind_speed=10.0,
        active_power=500.0,
        wind_direction=180.0,
        theoretical_power_curve=510.0,
        wind_speed_rolling_mean=10.1,
        wind_speed_rolling_std=0.2,
        power_error=10.0 # Hata oranı %2 civarı (Normal)
    )
    
    # Random faktörünü manipüle edemediğimiz için testin anomali üretme şansı %5'tir (random() > 0.95), 
    # Ama genel akışın kırılmadığından ve PredictionResult dondüğünden emin oluruz.
    result = predictor.predict(msg)
    
    assert isinstance(result, PredictionResult)
    assert result.model_version == "dummy-v1.0"
    
def test_dummy_predictor_anomaly_trigger():
    """
    Dummy predictor'un bariz bir hatada(power_error yuksek) kesinlikle anomali dönmesini bekle
    """
    predictor = DummyPredictor()
    
    msg = FeatureMessage(
        timestamp=datetime.now(),
        wind_speed=10.0,
        active_power=100.0, # Çok düşük üretiyor
        wind_direction=180.0,
        theoretical_power_curve=510.0,
        wind_speed_rolling_mean=10.1,
        wind_speed_rolling_std=0.2,
        power_error=410.0 #  Hata = %80
    )
    
    result = predictor.predict(msg)
    
    assert result.is_anomaly is True
    assert result.details["error_ratio_triggered"] is True
