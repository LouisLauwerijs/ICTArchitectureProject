"""
Reporting Service (Read-Side)

Verantwoordelijk voor:
- Luisteren naar RabbitMQ events
- Updaten van ReportingDB met read models
- Verstrekken van rapportage-endpoints
"""

import json
import logging
import os
import threading
import time
from datetime import datetime

import pika
import psycopg2
from flask import Flask, jsonify
from psycopg2 import OperationalError
from psycopg2.extras import RealDictCursor

EVENT_EXCHANGE = os.getenv("EVENT_EXCHANGE", "events")
EVENT_EXCHANGE_TYPE = "topic"
REPORTING_QUEUE = os.getenv("REPORTING_QUEUE", "reporting-events")
REPORTING_BINDING_KEY = os.getenv("REPORTING_BINDING_KEY", "order.*")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
event_consumer_running = False


def get_reporting_db_connection():
    """Verbind met ReportingDB (read-side database)."""
    return psycopg2.connect(
        host=os.getenv("REPORTINGDB_HOST", "reportingdb"),
        database=os.getenv("REPORTINGDB_NAME", "reportingdb"),
        user=os.getenv("REPORTINGDB_USER", "reportinguser"),
        password=os.getenv("REPORTINGDB_PASSWORD", "reportingpass"),
        port=os.getenv("REPORTINGDB_PORT", "5432"),
    )


def get_rabbitmq_connection():
    """Verbind met RabbitMQ."""
    credentials = pika.PlainCredentials(
        username=os.getenv("RABBITMQ_USER", "guest"),
        password=os.getenv("RABBITMQ_PASSWORD", "guest"),
    )
    parameters = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        credentials=credentials,
        connection_attempts=5,
        retry_delay=2,
    )
    return pika.BlockingConnection(parameters)


def check_reporting_dependencies():
    """Controleer of ReportingDB en RabbitMQ bereikbaar zijn."""
    db_conn = None
    rabbit_conn = None
    try:
        db_conn = get_reporting_db_connection()
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT 1;")

        rabbit_conn = get_rabbitmq_connection()
        return True, None
    except Exception as exc:
        return False, str(exc)
    finally:
        if db_conn:
            db_conn.close()
        if rabbit_conn:
            rabbit_conn.close()


def parse_order_date(timestamp_value):
    """Maak een consistente order-datum uit het eventtimestamp."""
    if not timestamp_value:
        return datetime.utcnow().date().isoformat()
    normalized = timestamp_value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).date().isoformat()


def handle_order_placed_event(event_data):
    """Consumeer een event en werk de reporting tabellen transactioneel bij."""
    conn = None
    cursor = None

    order_id = event_data.get("order_id")
    restaurant_id = event_data.get("restaurant_id")
    status = event_data.get("status", "placed")
    event_type = event_data.get("event_type", "unknown")
    total_price = float(event_data.get("total_price", 0))
    order_date = parse_order_date(event_data.get("timestamp"))

    try:
        logger.info(
            "Processing event: event_type=%s order_id=%s restaurant_id=%s total_price=%.2f order_date=%s",
            event_type,
            order_id,
            restaurant_id,
            total_price,
            order_date,
        )

        conn = get_reporting_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO revenue_per_day (date, total_revenue, order_count)
            VALUES (%s, %s, 1)
            ON CONFLICT (date) DO UPDATE SET
                total_revenue = revenue_per_day.total_revenue + EXCLUDED.total_revenue,
                order_count = revenue_per_day.order_count + EXCLUDED.order_count,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (order_date, total_price),
        )
        logger.info("ReportingDB upsert ok: table=revenue_per_day date=%s", order_date)

        cursor.execute(
            """
            INSERT INTO orders_per_restaurant (restaurant_id, order_count, total_revenue)
            VALUES (%s, 1, %s)
            ON CONFLICT (restaurant_id) DO UPDATE SET
                order_count = orders_per_restaurant.order_count + EXCLUDED.order_count,
                total_revenue = orders_per_restaurant.total_revenue + EXCLUDED.total_revenue,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (restaurant_id, total_price),
        )
        logger.info(
            "ReportingDB upsert ok: table=orders_per_restaurant restaurant_id=%s",
            restaurant_id,
        )

        cursor.execute(
            """
            INSERT INTO order_status_summary (status, count)
            VALUES (%s, 1)
            ON CONFLICT (status) DO UPDATE SET
                count = order_status_summary.count + EXCLUDED.count,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (status,),
        )
        logger.info("ReportingDB upsert ok: table=order_status_summary status=%s", status)

        cursor.execute(
            """
            INSERT INTO event_log (event_type, order_id, processed_at)
            VALUES (%s, %s, %s);
            """,
            (event_type, order_id, datetime.utcnow()),
        )
        logger.info("ReportingDB insert ok: table=event_log order_id=%s", order_id)

        conn.commit()
        logger.info("ReportingDB transaction committed: order_id=%s", order_id)
    except Exception as exc:
        if conn:
            conn.rollback()
            logger.info("ReportingDB transaction rolled back: order_id=%s", order_id)
        logger.error("Error handling event for order_id=%s: %s", order_id, exc, exc_info=True)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def event_consumer_worker():
    """Luister in een background thread naar RabbitMQ events."""
    global event_consumer_running

    logger.info("Event consumer worker starting")

    while True:
        connection = None
        channel = None
        try:
            logger.info(
                "Connecting RabbitMQ consumer: exchange=%s queue=%s binding_key=%s",
                EVENT_EXCHANGE,
                REPORTING_QUEUE,
                REPORTING_BINDING_KEY,
            )
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)

            channel.exchange_declare(
                exchange=EVENT_EXCHANGE,
                exchange_type=EVENT_EXCHANGE_TYPE,
                durable=True,
            )
            channel.queue_declare(queue=REPORTING_QUEUE, durable=True)
            channel.queue_bind(
                exchange=EVENT_EXCHANGE,
                queue=REPORTING_QUEUE,
                routing_key=REPORTING_BINDING_KEY,
            )

            def on_message(ch, method, properties, body):
                logger.info(
                    "Received event from RabbitMQ: delivery_tag=%s routing_key=%s content_type=%s body=%s",
                    method.delivery_tag,
                    method.routing_key,
                    getattr(properties, "content_type", None),
                    body.decode("utf-8"),
                )
                try:
                    event_data = json.loads(body)
                    handle_order_placed_event(event_data)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info("ACK sent for delivery_tag=%s order_id=%s", method.delivery_tag, event_data.get("order_id"))
                except json.JSONDecodeError as exc:
                    logger.error("Invalid JSON payload, dropping message: %s", exc, exc_info=True)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    logger.info("NACK sent with requeue=False for invalid JSON delivery_tag=%s", method.delivery_tag)
                except OperationalError as exc:
                    logger.error("Transient DB error, requeueing message: %s", exc, exc_info=True)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    logger.info("NACK sent with requeue=True for delivery_tag=%s", method.delivery_tag)
                except Exception as exc:
                    logger.error("Non-retryable processing error, dropping message: %s", exc, exc_info=True)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    logger.info("NACK sent with requeue=False for delivery_tag=%s", method.delivery_tag)

            channel.basic_consume(
                queue=REPORTING_QUEUE,
                on_message_callback=on_message,
                auto_ack=False,
            )

            event_consumer_running = True
            logger.info(
                "Event consumer listening on queue '%s' bound to exchange '%s' with routing_key '%s'",
                REPORTING_QUEUE,
                EVENT_EXCHANGE,
                REPORTING_BINDING_KEY,
            )
            channel.start_consuming()
        except Exception as exc:
            event_consumer_running = False
            logger.error("Event consumer error: %s", exc, exc_info=True)
            logger.info("Retrying RabbitMQ connection in 5 seconds")
            time.sleep(5)
        finally:
            try:
                if channel and channel.is_open:
                    channel.close()
            except Exception:
                pass
            try:
                if connection and connection.is_open:
                    connection.close()
            except Exception:
                pass


@app.route("/health", methods=["GET"])
def health():
    dependencies_ready, error = check_reporting_dependencies()
    status = "healthy" if dependencies_ready and event_consumer_running else "degraded"
    return jsonify(
        {
            "status": status,
            "service": "reporting-service",
            "event_consumer_running": event_consumer_running,
            "dependencies_ready": dependencies_ready,
            **({"error": error} if error else {}),
        }
    ), (200 if status == "healthy" else 503)


@app.route("/reports/revenue-by-day", methods=["GET"])
def get_revenue_by_day():
    try:
        conn = get_reporting_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT date, total_revenue, order_count
            FROM revenue_per_day
            ORDER BY date DESC
            LIMIT 30;
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"data": [dict(row) for row in rows], "count": len(rows)}), 200
    except Exception as exc:
        logger.error("Error fetching revenue-by-day: %s", exc, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/reports/revenue-by-restaurant", methods=["GET"])
def get_revenue_by_restaurant():
    try:
        conn = get_reporting_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT restaurant_id, order_count, total_revenue
            FROM orders_per_restaurant
            ORDER BY total_revenue DESC;
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"data": [dict(row) for row in rows], "count": len(rows)}), 200
    except Exception as exc:
        logger.error("Error fetching revenue-by-restaurant: %s", exc, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/reports/order-status-summary", methods=["GET"])
def get_order_status_summary():
    try:
        conn = get_reporting_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT status, count
            FROM order_status_summary
            ORDER BY count DESC;
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"data": [dict(row) for row in rows], "count": len(rows)}), 200
    except Exception as exc:
        logger.error("Error fetching order-status-summary: %s", exc, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/reports/event-log", methods=["GET"])
def get_event_log():
    try:
        conn = get_reporting_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT event_type, order_id, processed_at
            FROM event_log
            ORDER BY processed_at DESC
            LIMIT 50;
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"data": [dict(row) for row in rows], "count": len(rows)}), 200
    except Exception as exc:
        logger.error("Error fetching event-log: %s", exc, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    consumer_thread = threading.Thread(target=event_consumer_worker, daemon=True)
    consumer_thread.start()
    app.run(host="0.0.0.0", port=5002, debug=False)
