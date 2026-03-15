# ──────────────────────────────────────────────────────
# exceptions.py — Özel Hata Sınıfları (SRP + Güvenlik)
# ──────────────────────────────────────────────────────
#
# SRP UYGULAMASI:
#   Hata yönetimi tek bir yerde toplanır.
#   Her modül kendi hata tipini fırlatır,
#   API katmanı bunları HTTP yanıtlarına dönüştürür.
#
# GÜVENLİK:
#   - Özel hata sınıfları sayesinde dahili hata detayları
#     (dosya yolu, SQL sorgusu vb.) kullanıcıya SIZDIRMAZ.
#   - API katmanı sadece güvenli mesajları döner.
#   - OWASP A09:2021 — Security Logging and Monitoring Failures
#     → Her hata loglanır ama detaylar kullanıcıya gösterilmez.
# ──────────────────────────────────────────────────────


class WindSentinelError(Exception):
    """
    Tüm proje hatalarının temel sınıfı.

    Neden özel hata sınıfı?
    → Python'un genel Exception sınıfı çok genel.
    → Kendi hata tipimizi tanımlayarak, hataları
      türlerine göre ayırt edip farklı işleyebiliriz.
    """

    def __init__(self, message: str, detail: str = None):
        """
        Args:
            message: Kullanıcıya gösterilebilecek GÜVENLI mesaj
            detail: Sadece LOGLARDA görünecek dahili detay (güvenlik!)
        """
        self.message = message
        self.detail = detail  # Bu bilgi asla API yanıtında gönderilmez!
        super().__init__(self.message)


class BrokerConnectionError(WindSentinelError):
    """RabbitMQ bağlantı hatası."""
    pass


class BrokerPublishError(WindSentinelError):
    """RabbitMQ mesaj gönderme hatası."""
    pass


class DataSourceNotFoundError(WindSentinelError):
    """Veri kaynağı (CSV dosyası) bulunamadı."""
    pass


class DataReadError(WindSentinelError):
    """Veri okuma sırasında oluşan hata."""
    pass


class InvalidAssetIdError(WindSentinelError):
    """
    Geçersiz veya izin verilmeyen asset_id.

    GÜVENLİK:
    → Whitelist'te olmayan asset_id'ler reddedilir.
    → Path traversal saldırılarını engeller.
      Örnek: asset_id = "../../../etc/passwd" gibi bir değer
      ile dosya sistemi taranması engellenmiş olur.
    """
    pass


class IngestionAlreadyRunningError(WindSentinelError):
    """Zaten bir ingestion işlemi çalışıyor."""
    pass
