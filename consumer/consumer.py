import os
import json
import time
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
import pika
from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError
import psycopg2
from psycopg2 import sql

from data_sources.factory import DataSourceFactory

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

shutdown_event = False


class ConsumerSettings(BaseSettings):
    """Configuration for the Data Consumer."""

    # RabbitMQ Connection
    rabbitmq_host: str = Field(
        default="rabbitmq",
        description="RabbitMQ host address"
    )
    rabbitmq_user: str = Field(
        default="guest",
        description="RabbitMQ username"
    )
    rabbitmq_password: str = Field(
        default="guest",
        description="RabbitMQ password"
    )

    # Queues
    input_queue: str = Field(
        default="sensor-data",
        description="Queue to consume raw sensor data from"
    )
    output_queue: str = Field(
        default="measurement.raw",
        description="Queue to publish processed data to"
    )
    exchange_name: str = Field(
        default="wind.events",
        description="RabbitMQ exchange name"
    )
    routing_key: str = Field(
        default="measurement.raw",
        description="Routing key for output messages"
    )

    # Processing
    poll_interval: int = Field(
        default=1,
        description="Seconds between polling for messages"
    )
    ack_timeout: int = Field(
        default=5,
        description="Timeout in seconds for processing a message"
    )

    # Database
    db_host: str = Field(
        default="postgres",
        description="PostgreSQL host"
    )
    db_port: int = Field(
        default=5432,
        description="PostgreSQL port"
    )
    db_name: str = Field(
        default="windsentinel",
        description="PostgreSQL database name"
    )
    db_user: str = Field(
        default="postgres",
        description="PostgreSQL username"
    )
    db_password: str = Field(
        default="postgres",
        description="PostgreSQL password"
    )

    # Data Source
    data_source_type: str = Field(
        default="csv",
        description="Data source type (csv or excel)"
    )
    data_file_path: str = Field(
        default="/data/dataset.csv",
        description="Path to data file for seeding"
    )

    class Config:
        env_prefix = ""
        case_sensitive = False


def handle_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    global shutdown_event
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event = True


def validate_message_structure(message_body: Dict[str, Any]) -> bool:
    """Validate incoming message structure."""
    required_fields = ["batch_index", "sent_at", "row_count", "data"]
    for field in required_fields:
        if field not in message_body:
            logger.error(f"Missing required field: {field}")
            return False

    if not isinstance(message_body.get("data"), list):
        logger.error("Field 'data' must be a list")
        return False

    if len(message_body["data"]) != message_body.get("row_count", 0):
        logger.warning(
            f"row_count mismatch: expected {message_body['row_count']}, "
            f"got {len(message_body['data'])}"
        )

    return True


def transform_sensor_data(message_body: Dict[str, Any]) -> Optional[list]:
    """
    Transform sensor data to measurement format for the pipeline.

    Converts batch of CSV rows to individual measurement objects.
    Enriches missing fields from the simple CSV format to match Feature Service schema.
    Returns a list of JSON strings (one per measurement).
    """
    try:
        transformed_list = []
        for measurement in message_body.get("data", []):
            # Enrich the measurement with missing fields
            asset_id = int(measurement.get("asset_id", 0))
            turbine_id = f"WFA-T{str(asset_id).zfill(2)}"

            enriched_data = {
                "timestamp": measurement.get("timestamp", ""),
                "asset_id": asset_id,
                "turbine_id": turbine_id,
                "status_type_id": int(measurement.get("status_type_id", 0)),
                "wind_speed": _safe_float(measurement.get("wind_speed")),
                "power_output": _safe_float(measurement.get("power_output")),
                # Synthetic values - in real scenario, these come from SCADA CSV
                "generator_rpm": _safe_float(measurement.get("generator_rpm", "0")) or 1500.0,
                "total_active_power": _safe_float(measurement.get("power_output", "0")) * 1000,  # kW to Wh
                "reactive_power_inductive": _safe_float(measurement.get("temperature", "0")) * 10,  # synthetic
                "reactive_power_capacitive": _safe_float(measurement.get("humidity", "0")) * 5,  # synthetic
                "rotor_rpm": _safe_float(measurement.get("rotor_rpm", "0")) or 12.0,
                "gearbox_oil_temp": _safe_float(measurement.get("temperature", "0")) or 25.0,
            }
            transformed_list.append(json.dumps(enriched_data))

        return transformed_list
    except Exception as e:
        logger.error(f"Error transforming data: {e}", exc_info=True)
        return None


def _safe_float(value) -> float:
    """Convert value to float safely. Invalid → 0.0"""
    try:
        if value is None or value == "":
            return 0.0
        result = float(value)
        if result != result:  # NaN check
            return 0.0
        return round(result, 6)
    except (ValueError, TypeError):
        return 0.0


def get_db_connection(settings: ConsumerSettings):
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None


def check_seed_exists(conn) -> bool:
    """Check if seed flag exists in database."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'seed_status')"
        )
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    except Exception as e:
        logger.debug(f"Error checking seed status: {e}")
        return False


def create_seed_table(conn):
    """Create seed_status and measurements tables if they don't exist."""
    try:
        cursor = conn.cursor()

        # Create seed_status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seed_status (
                id SERIAL PRIMARY KEY,
                seeded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_source TEXT
            )
        """)

        # Create measurements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                id SERIAL PRIMARY KEY,
                timestamp VARCHAR(50) NOT NULL,
                asset_id INTEGER NOT NULL,
                turbine_id VARCHAR(20) NOT NULL,
                status_type_id INTEGER NOT NULL,
                wind_speed FLOAT NOT NULL,
                power_output FLOAT NOT NULL,
                generator_rpm FLOAT NOT NULL,
                total_active_power FLOAT NOT NULL,
                reactive_power_inductive FLOAT NOT NULL,
                reactive_power_capacitive FLOAT NOT NULL,
                rotor_rpm FLOAT NOT NULL,
                gearbox_oil_temp FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, asset_id)
            )
        """)

        conn.commit()
        cursor.close()
    except Exception as e:
        logger.error(f"Error creating tables: {e}")


def seed_database(settings: ConsumerSettings):
    """Load and insert initial data into database if not already seeded."""
    logger.info("Starting seed check...")

    try:
        conn = get_db_connection(settings)
        if not conn:
            logger.warning("Skipping seed: database connection failed")
            return

        # Create seed status table
        create_seed_table(conn)

        # Check if already seeded
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM seed_status")
        count = cursor.fetchone()[0]
        cursor.close()

        if count > 0:
            logger.info("✓ Seed already exists, skipping")
            conn.close()
            return

        # Load data from source
        logger.info(f"Seeding database from {settings.data_source_type}...")
        rows = DataSourceFactory.load(settings.data_file_path)

        if not rows:
            logger.warning("No rows to seed, skipping")
            conn.close()
            return

        # Insert rows into database
        cursor = conn.cursor()
        try:
            for row in rows:
                # Prepare enriched data (same logic as transform_sensor_data)
                asset_id = int(row.get("asset_id", 0))
                turbine_id = f"WFA-T{str(asset_id).zfill(2)}"

                enriched = {
                    "timestamp": row.get("timestamp", ""),
                    "asset_id": asset_id,
                    "turbine_id": turbine_id,
                    "status_type_id": int(row.get("status_type_id", 0)),
                    "wind_speed": _safe_float(row.get("wind_speed")),
                    "power_output": _safe_float(row.get("power_output")),
                    "generator_rpm": _safe_float(row.get("generator_rpm", "0")) or 1500.0,
                    "total_active_power": _safe_float(row.get("power_output", "0")) * 1000,
                    "reactive_power_inductive": _safe_float(row.get("temperature", "0")) * 10,
                    "reactive_power_capacitive": _safe_float(row.get("humidity", "0")) * 5,
                    "rotor_rpm": _safe_float(row.get("rotor_rpm", "0")) or 12.0,
                    "gearbox_oil_temp": _safe_float(row.get("temperature", "0")) or 25.0,
                }

                # Insert into database
                insert_sql = """
                    INSERT INTO measurements (
                        timestamp, asset_id, turbine_id, status_type_id,
                        wind_speed, power_output, generator_rpm, total_active_power,
                        reactive_power_inductive, reactive_power_capacitive,
                        rotor_rpm, gearbox_oil_temp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """
                cursor.execute(insert_sql, (
                    enriched["timestamp"],
                    enriched["asset_id"],
                    enriched["turbine_id"],
                    enriched["status_type_id"],
                    enriched["wind_speed"],
                    enriched["power_output"],
                    enriched["generator_rpm"],
                    enriched["total_active_power"],
                    enriched["reactive_power_inductive"],
                    enriched["reactive_power_capacitive"],
                    enriched["rotor_rpm"],
                    enriched["gearbox_oil_temp"],
                ))

            conn.commit()
            logger.info(f"✓ Seeded {len(rows)} measurements into database")

            # Mark as seeded
            cursor.execute(
                "INSERT INTO seed_status (data_source) VALUES (%s)",
                (settings.data_source_type,)
            )
            conn.commit()

        except Exception as e:
            logger.error(f"Error during seeding: {e}", exc_info=True)
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Database seeding failed: {e}", exc_info=True)


def create_connection(settings: ConsumerSettings) -> pika.BlockingConnection:
    """Create and return a RabbitMQ connection."""
    credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.rabbitmq_host,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
            connection_attempts=1,
        )
    )
    return connection


def wait_for_rabbitmq(settings: ConsumerSettings):
    """Wait until RabbitMQ is available with exponential backoff."""
    max_retries = 30
    base_delay = 1
    max_delay = 10

    for attempt in range(max_retries):
        try:
            credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.rabbitmq_host,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300,
                    connection_attempts=1,
                )
            )
            connection.close()
            logger.info("Successfully connected to RabbitMQ")
            return
        except (pika.exceptions.AMQPConnectionError, Exception) as e:
            retry_delay = min(base_delay * (2 ** attempt), max_delay)
            if attempt < max_retries - 1:
                logger.debug(
                    f"RabbitMQ not ready (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {retry_delay}s: {type(e).__name__}"
                )
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"Failed to connect to RabbitMQ after {max_retries} attempts: {e}",
                    exc_info=True
                )
                raise


def setup_queue(channel: pika.adapters.blocking_connection.BlockingChannel, settings: ConsumerSettings):
    """Passively declare input queue (verify it exists without modifying)."""
    try:
        # Passive declare - just verify queue exists, don't modify its configuration
        channel.queue_declare(queue=settings.input_queue, passive=True)
        logger.info(f"Queue '{settings.input_queue}' verified to exist")
    except pika.exceptions.ChannelClosedByBroker as e:
        logger.error(f"Queue '{settings.input_queue}' not found or config mismatch: {e}")
        raise
    except Exception as e:
        logger.error(f"Error verifying queue: {e}", exc_info=True)
        raise


def message_callback(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    method: pika.spec.Basic.Deliver,
    properties: pika.spec.BasicProperties,
    body: bytes,
    settings: ConsumerSettings
):
    """Callback function for processing messages."""
    global shutdown_event

    if shutdown_event:
        logger.info("Shutdown signal received, not processing new messages")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return

    try:
        # Parse message
        message_body = json.loads(body.decode("utf-8"))
        batch_index = message_body.get("batch_index", -1)

        logger.info(
            f"Received message: batch_index={batch_index}, "
            f"row_count={message_body.get('row_count')}"
        )

        # Validate structure
        if not validate_message_structure(message_body):
            logger.warning(f"Message validation failed for batch {batch_index}, rejecting")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        # Transform data - returns list of individual measurements
        transformed_list = transform_sensor_data(message_body)
        if transformed_list is None:
            logger.error(f"Failed to transform batch {batch_index}, rejecting")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        # Publish each measurement individually to output queue
        try:
            for idx, transformed_json in enumerate(transformed_list):
                channel.basic_publish(
                    exchange=settings.exchange_name,
                    routing_key=settings.routing_key,
                    body=transformed_json,
                    properties=pika.BasicProperties(
                        delivery_mode=pika.DeliveryMode.Persistent,
                        content_type="application/json"
                    )
                )
            logger.info(
                f"Published batch {batch_index} ({len(transformed_list)} measurements) "
                f"to queue '{settings.output_queue}'"
            )
        except Exception as e:
            logger.error(
                f"Failed to publish batch {batch_index} to output queue: {e}",
                exc_info=True
            )
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        # Acknowledge message after successful processing
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.debug(f"Acknowledged batch {batch_index}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON message: {e}", exc_info=True)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Unexpected error processing message: {e}", exc_info=True)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """Main consumer loop with polling-based message consumption."""
    global shutdown_event

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Load settings
    try:
        settings = ConsumerSettings()
    except ValidationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    logger.info("Starting Data Consumer")
    logger.info(f"  Input Queue: {settings.input_queue}")
    logger.info(f"  Output Queue: {settings.output_queue}")
    logger.info(f"  Exchange: {settings.exchange_name}")
    logger.info(f"  RabbitMQ Host: {settings.rabbitmq_host}")
    logger.info(f"  Poll Interval: {settings.poll_interval}s")

    # Wait for RabbitMQ
    try:
        wait_for_rabbitmq(settings)
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ during startup: {e}")
        sys.exit(1)

    # Seed database on startup
    seed_database(settings)

    connection = None
    channel = None
    reconnect_attempt = 0
    base_delay = 1
    max_delay = 10

    try:
        logger.info(f"Listening on queue '{settings.input_queue}'...")

        while not shutdown_event:
            try:
                # Reconnect if needed
                if connection is None or connection.is_closed or (channel and channel.is_closed):
                    logger.info("Establishing RabbitMQ connection...")
                    try:
                        connection = create_connection(settings)
                        channel = connection.channel()
                        channel.basic_qos(prefetch_count=1)

                        # Passively declare queue to verify it exists
                        setup_queue(channel, settings)

                        logger.info("RabbitMQ connection established successfully")
                        reconnect_attempt = 0
                    except (pika.exceptions.AMQPConnectionError, pika.exceptions.ChannelClosedByBroker, Exception) as e:
                        reconnect_delay = min(base_delay * (2 ** reconnect_attempt), max_delay)
                        logger.warning(
                            f"Failed to connect (attempt {reconnect_attempt + 1}), "
                            f"retrying in {reconnect_delay}s: {type(e).__name__}"
                        )
                        connection = None
                        channel = None
                        reconnect_attempt += 1
                        time.sleep(reconnect_delay)
                        continue

                if shutdown_event:
                    logger.info("Shutdown signal received, stopping consumer")
                    if channel and not channel.is_closed:
                        try:
                            channel.stop_consuming()
                        except:
                            pass
                    break

                # Set up consumer callback
                logger.info(f"Listening on queue '{settings.input_queue}'...")
                channel.basic_consume(
                    queue=settings.input_queue,
                    on_message_callback=lambda ch, method, props, body: message_callback(
                        ch, method, props, body, settings
                    ),
                    auto_ack=False
                )

                # Start blocking consumer loop
                try:
                    channel.start_consuming()
                except pika.exceptions.ChannelClosedByBroker as e:
                    logger.warning(f"Channel closed by broker: {e}")
                    connection = None
                    channel = None
                except pika.exceptions.AMQPConnectionError as e:
                    logger.warning(f"Connection lost: {type(e).__name__}")
                    connection = None
                    channel = None
                except Exception as e:
                    logger.error(f"Error during consumption: {e}", exc_info=True)
                    connection = None
                    channel = None

            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                connection = None
                channel = None
                time.sleep(5)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if channel and not channel.is_closed:
            try:
                channel.stop_consuming()
            except:
                pass

        if connection and not connection.is_closed:
            try:
                connection.close()
                logger.info("RabbitMQ connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

        logger.info("Data Consumer stopped")


if __name__ == "__main__":
    main()
