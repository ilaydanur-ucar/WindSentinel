from abc import ABC, abstractmethod
from app.models.schemas import AlarmMessage

class BaseNotifier(ABC):
    """
    Tüm bildirim kanalları için (Email, Log, Slack vb.) temel arayüz.
    Strategy Pattern uygulayarak yeni kanalların kolayca eklenmesini sağlar.
    """
    
    @abstractmethod
    async def notify(self, alarm: AlarmMessage) -> bool:
        """
        Bildirimi gönderir. 
        Başarılı ise True, aksi halde False döner.
        """
        pass
