import os
import csv
import json
import time
import logging
import signal
import sys
from datetime import datetime, timezone
import pika

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

shutdown_event = False

# Configuration from environment variables
CSV_PATH = "/data/dataset.csv"
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "600"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "sensor-data")


def handle_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    global shutdown_event
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event = True


def load_csv_rows():
    """Load all rows from CSV file with BOM handling."""
    rows = []
    try:
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        logger.info(f"Loaded {len(rows)} rows from {CSV_PATH}")
    except FileNotFoundError:
        logger.error(f"CSV file not found at {CSV_PATH}")
        raise
    except ValueError as e:
        logger.error(f"CSV format error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}", exc_info=True)
        raise
    return rows


def wait_for_rabbitmq():
    """Wait until RabbitMQ is available with exponential backoff."""
    max_retries = 30
    base_delay = 1
    max_delay = 10

    for attempt in range(max_retries):
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
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


def create_connection():
    """Create and return a RabbitMQ connection."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
            connection_attempts=1,
        )
    )
    return connection


def establish_channel_with_queue(connection):
    """Create a channel and declare the queue."""
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    logger.debug(f"Channel established and queue '{RABBITMQ_QUEUE}' declared")
    return channel


def publish_batch(channel, batch_index, rows):
    """Publish a batch of rows to RabbitMQ."""
    message = {
        "batch_index": batch_index,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "data": rows,
    }

    try:
        channel.basic_publish(
            exchange="",
            routing_key=RABBITMQ_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent
            ),
        )
        logger.info(
            f"Published batch {batch_index} with {len(rows)} rows to queue '{RABBITMQ_QUEUE}'"
        )
    except Exception as e:
        logger.error(f"Error publishing batch {batch_index}: {e}")
        raise


def main():
    """Main simulator loop with graceful shutdown."""
    global shutdown_event

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info("Starting Data Simulator")
    logger.info(f"  CSV Path: {CSV_PATH}")
    logger.info(f"  Interval: {INTERVAL_SECONDS} seconds")
    logger.info(f"  Batch Size: {BATCH_SIZE}")
    logger.info(f"  RabbitMQ Host: {RABBITMQ_HOST}")
    logger.info(f"  Queue: {RABBITMQ_QUEUE}")

    try:
        wait_for_rabbitmq()
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ during startup: {e}")
        sys.exit(1)

    try:
        rows = load_csv_rows()
    except Exception as e:
        logger.error(f"Failed to load CSV file: {e}")
        sys.exit(1)

    if not rows:
        logger.error("No rows loaded from CSV file")
        sys.exit(1)

    batch_index = 0
    row_index = 0
    connection = None
    channel = None
    reconnect_attempt = 0
    base_delay = 1
    max_delay = 10

    try:
        while not shutdown_event:
            try:
                if connection is None or connection.is_closed:
                    logger.info("Establishing RabbitMQ connection...")
                    try:
                        connection = create_connection()
                        channel = establish_channel_with_queue(connection)
                        logger.info("RabbitMQ connection established successfully")
                        reconnect_attempt = 0
                    except (pika.exceptions.AMQPConnectionError, Exception) as e:
                        reconnect_delay = min(base_delay * (2 ** reconnect_attempt), max_delay)
                        logger.warning(
                            f"Failed to connect to RabbitMQ (attempt {reconnect_attempt + 1}), "
                            f"retrying in {reconnect_delay}s: {type(e).__name__}"
                        )
                        reconnect_attempt += 1
                        time.sleep(reconnect_delay)
                        continue

                if shutdown_event:
                    logger.info("Shutdown signal received, exiting gracefully")
                    break

                batch_rows = []
                for _ in range(BATCH_SIZE):
                    if row_index >= len(rows):
                        row_index = 0
                        logger.info("Looping CSV file back to beginning")
                    batch_rows.append(rows[row_index])
                    row_index += 1

                try:
                    publish_batch(channel, batch_index, batch_rows)
                    batch_index += 1
                except (pika.exceptions.AMQPError, Exception) as e:
                    logger.warning(f"Failed to publish batch: {type(e).__name__}, will reconnect")
                    connection = None
                    channel = None
                    continue

                logger.debug(f"Waiting {INTERVAL_SECONDS} seconds until next batch...")
                for _ in range(INTERVAL_SECONDS):
                    if shutdown_event:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                connection = None
                channel = None
                time.sleep(5)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if connection and not connection.is_closed:
            try:
                connection.close()
                logger.info("RabbitMQ connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
        logger.info("Data Simulator stopped")


if __name__ == "__main__":
    main()
