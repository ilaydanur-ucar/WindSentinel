# ──────────────────────────────────────────────────────────────
# dependencies.py — Dependency Injection Container (DIP)
# ──────────────────────────────────────────────────────────────
#
# DIP UYGULAMASI:
#   Bu dosya tüm bağımlılıkları oluşturur ve birbirine bağlar.
#   "Composition Root" olarak bilinir — uygulamanın DI merkezi.
#
#   Bağlantı Grafiği:
#     RabbitMQClient ──→ IMessageBroker ──┐
#                                          ├──→ IngestionService
#     ScadaCsvReader ──→ IDataReader ─────┘
#
#   FastAPI'nin Depends() mekanizması ile route'lara enjekte edilir.
#
# Neden Dependency Injection?
#   1. TEST: Test yazarken gerçek RabbitMQ yerine mock kullanabilirsin
#   2. DEĞİŞİKLİK: RabbitMQ → Kafka geçişinde sadece bu dosya değişir
#   3. BAĞIMSIZLIK: Her modül bağımsız geliştirilebilir ve test edilebilir
# ──────────────────────────────────────────────────────────────

from app.rabbitmq_client import RabbitMQClient
from app.csv_reader import ScadaCsvReader
from app.ingestion_service import IngestionService

# ──────────────────────────────────────────────────────
# Singleton Instances (Uygulama boyunca tek nesne)
# ──────────────────────────────────────────────────────
# Bu nesneler uygulama başladığında oluşturulur ve
# uygulama kapanana kadar yaşar.

# Concrete implementations (somut sınıflar)
rabbitmq_client = RabbitMQClient()
csv_reader = ScadaCsvReader()

# Business logic (iş mantığı) — interface'ler üzerinden bağlanır
ingestion_service = IngestionService(
    broker=rabbitmq_client,  # IMessageBroker olarak enjekte
    reader=csv_reader,       # IDataReader olarak enjekte
)


def get_ingestion_service() -> IngestionService:
    """
    FastAPI Depends() ile kullanılacak dependency provider.

    Route'larda şöyle kullanılır:
        @router.post("/ingest")
        async def ingest(service: IngestionService = Depends(get_ingestion_service)):
            ...

    Bu pattern sayesinde:
    - Route fonksiyonları IngestionService'in nasıl oluşturulduğunu bilmez
    - Test'te farklı bir service enjekte edilebilir
    """
    return ingestion_service


def get_rabbitmq_client() -> RabbitMQClient:
    """RabbitMQ client'ına erişim (lifespan için gerekli)."""
    return rabbitmq_client
