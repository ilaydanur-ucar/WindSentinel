# ──────────────────────────────────────────────────────────────
# interfaces.py — Soyut Arayüzler (Dependency Inversion Principle)
# ──────────────────────────────────────────────────────────────
#
# DEPENDENCY INVERSION PRENSİBİ (DIP):
#   "Yüksek seviyeli modüller, düşük seviyeli modüllere bağımlı
#    olmamalıdır. Her ikisi de SOYUTLAMALARA bağımlı olmalıdır."
#
# Ne Demek Bu?
#   ingestion_service.py (yüksek seviye — iş mantığı) doğrudan
#   rabbitmq_client.py'ye (düşük seviye — altyapı) bağımlı olmamalı.
#
#   Bunun yerine her ikisi de bir INTERFACE'e bağımlı olmalı:
#
#   ✗ YANLIŞ:  IngestionService → RabbitMQClient (somut sınıfa bağımlı)
#   ✓ DOĞRU:   IngestionService → IMessageBroker ← RabbitMQClient
#
#   Bu sayede:
#   - Test yazarken RabbitMQ yerine sahte (mock) client kullanabilirsin
#   - İleride RabbitMQ yerine Kafka'ya geçersen sadece yeni bir sınıf
#     yazarsın, iş mantığı koduna HİÇ dokunmazsın
#
# Python'da Interface = Protocol (typing modülünden)
#   Protocol sınıfı, bir sınıfın hangi metotlara sahip olması
#   gerektiğini tanımlar ama nasıl çalışacağını söylemez.
#   "Ne yapılacağını söyler, nasıl yapılacağını söylemez."
# ──────────────────────────────────────────────────────────────

from typing import Protocol, Generator


class IMessageBroker(Protocol):
    """
    Mesaj kuyruğu sistemi için soyut arayüz.

    Bu interface'i implemente eden herhangi bir sınıf
    (RabbitMQ, Kafka, Redis Streams...) kullanılabilir.

    Metotlar:
        connect()  → Broker'a bağlan
        publish()  → Mesaj gönder
        close()    → Bağlantıyı kapat
        is_connected → Bağlantı durumu
    """

    async def connect(self) -> None:
        """Mesaj broker'a bağlantı kur."""
        ...

    async def publish(self, message: dict) -> bool:
        """
        Mesaj gönder.

        Args:
            message: Gönderilecek mesaj (dict formatında)

        Returns:
            True → başarılı, False → başarısız
        """
        ...

    async def close(self) -> None:
        """Bağlantıyı düzgün kapat."""
        ...

    @property
    def is_connected(self) -> bool:
        """Bağlantının aktif olup olmadığı."""
        ...


class IDataReader(Protocol):
    """
    Veri okuyucu için soyut arayüz.

    Bu interface'i implemente eden herhangi bir sınıf
    (CSV okuyucu, veritabanı okuyucu, API okuyucu...)
    kullanılabilir.

    Metotlar:
        list_sources()    → Mevcut veri kaynaklarını listele
        read_chunks()     → Veriyi parçalar halinde oku
    """

    def list_sources(self) -> list[dict]:
        """
        Kullanılabilir veri kaynaklarını listele.

        Returns:
            [{"asset_id": 0, "filename": "...", "path": "..."}, ...]
        """
        ...

    def read_chunks(
        self,
        source_path: str,
        chunk_size: int,
    ) -> Generator[list[dict], None, None]:
        """
        Veri kaynağını parçalar halinde oku.

        Args:
            source_path: Veri kaynağının yolu
            chunk_size: Her parçadaki kayıt sayısı

        Yields:
            Her parça bir liste olarak döner: [{"timestamp": ..., ...}, ...]
        """
        ...
