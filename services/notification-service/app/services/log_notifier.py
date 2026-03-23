import logging
from app.services.base import BaseNotifier
from app.models.schemas import AlarmMessage

logger = logging.getLogger(__name__)

class LogNotifier(BaseNotifier):
    """
    Alarmları sadece uygulama loglarına yazan notifier.
    İlk aşama ve debug süreçleri için temel implementasyon.
    """
    
    async def notify(self, alarm: AlarmMessage) -> bool:
        try:
            # Alarm ciddiyetine göre log seviyesi belirle
            log_level = logging.INFO
            prefix = "🔔 [NOTIFICATION]"
            
            if alarm.severity == "CRITICAL":
                log_level = logging.ERROR
                prefix = "🚨 [CRITICAL ALERT]"
            elif alarm.severity == "WARNING":
                log_level = logging.WARNING
                prefix = "⚠️ [WARNING]"

            log_msg = (
                f"{prefix} Turbine: {alarm.turbine_id} (asset:{alarm.asset_id}) | "
                f"Type: {alarm.fault_type} | "
                f"Score: {alarm.confidence:.2f} | "
                f"Time: {alarm.timestamp}"
            )
            
            logger.log(log_level, log_msg)
            return True
        except Exception as e:
            logger.error(f"LogNotifier hatası: {e}")
            return False
