"""
Order Service (Write-Side)

Verantwoordelijk voor:
- Bestellingen aannemen van klanten (POST /order)
- Validatie van bestellingen
- Persisten naar OrderDB
- Publiceren van 'order.placed' events naar RabbitMQ
"""

import json
import logging
import os
import uuid
from datetime import datetime

import pika
import psycopg2
from flask import Flask, jsonify, request
from psycopg2.extras import RealDictCursor

EVENT_EXCHANGE = os.getenv("EVENT_EXCHANGE", "events")
EVENT_EXCHANGE_TYPE = "topic"
REPORTING_QUEUE = os.getenv("REPORTING_QUEUE", "reporting-events")
ORDER_ROUTING_KEY = os.getenv("ORDER_ROUTING_KEY", "order.placed")
REPORTING_BINDING_KEY = os.getenv("REPORTING_BINDING_KEY", "order.*")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def get_db_connection():
    """Verbind met OrderDB (write-side database)."""
    return psycopg2.connect(
        host=os.getenv("ORDERDB_HOST", "orderdb"),
        database=os.getenv("ORDERDB_NAME", "orderdb"),
        user=os.getenv("ORDERDB_USER", "orderuser"),
        password=os.getenv("ORDERDB_PASSWORD", "orderpass"),
        port=os.getenv("ORDERDB_PORT", "5432"),
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


def check_order_dependencies():
    """Controleer of OrderDB en RabbitMQ bereikbaar zijn."""
    db_conn = None
    rabbit_conn = None
    try:
        db_conn = get_db_connection()
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


def ensure_rabbitmq_setup():
    """Zorg dat de exchange, queue en binding bestaan."""
    connection = None
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
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
        logger.info(
            "RabbitMQ publisher setup ready: exchange=%s queue=%s publish_key=%s binding_key=%s",
            EVENT_EXCHANGE,
            REPORTING_QUEUE,
            ORDER_ROUTING_KEY,
            REPORTING_BINDING_KEY,
        )
    except Exception as exc:
        logger.warning("RabbitMQ setup could not be completed yet: %s", exc)
    finally:
        if connection:
            connection.close()


def publish_order_event(order_data):
    """Publiceer een 'order.placed' event naar RabbitMQ."""
    connection = None

    event = {
        "event_type": "order.placed",
        "order_id": order_data["order_id"],
        "restaurant_id": order_data["restaurant_id"],
        "customer_id": order_data["customer_id"],
        "total_price": order_data["total_price"],
        "status": order_data["status"],
        "timestamp": order_data["created_at"],
        "items": order_data["items"],
    }
    event_json = json.dumps(event)

    try:
        logger.info(
            "Publishing event: event_type=%s order_id=%s exchange=%s routing_key=%s queue=%s",
            event["event_type"],
            event["order_id"],
            EVENT_EXCHANGE,
            ORDER_ROUTING_KEY,
            REPORTING_QUEUE,
        )
        logger.info("Event payload: %s", event_json)

        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.confirm_delivery()

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

        channel.basic_publish(
            exchange=EVENT_EXCHANGE,
            routing_key=ORDER_ROUTING_KEY,
            body=event_json,
            mandatory=True,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )

        logger.info(
            "Event published successfully: order_id=%s exchange=%s routing_key=%s",
            event["order_id"],
            EVENT_EXCHANGE,
            ORDER_ROUTING_KEY,
        )
    except Exception as exc:
        logger.error("Failed to publish event for order_id=%s: %s", event["order_id"], exc, exc_info=True)
        raise
    finally:
        if connection:
            connection.close()


def create_order(restaurant_id, customer_id, items, total_price):
    """Valideer, sla op in OrderDB en publiceer een event."""
    if not restaurant_id or not customer_id:
        raise ValueError("restaurant_id en customer_id zijn verplicht")
    if not items:
        raise ValueError("Bestelling moet minstens 1 item bevatten")
    if total_price is None or float(total_price) <= 0:
        raise ValueError("total_price moet groter zijn dan 0")

    order_id = f"ORD-{str(uuid.uuid4())[:8].upper()}"
    created_at = datetime.utcnow().isoformat() + "Z"
    status = "placed"
    normalized_total = float(total_price)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO orders (
                order_id,
                restaurant_id,
                customer_id,
                total_price,
                status,
                items,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING order_id, created_at;
            """,
            (
                order_id,
                restaurant_id,
                customer_id,
                normalized_total,
                status,
                json.dumps(items),
                created_at,
            ),
        )
        conn.commit()
        logger.info("Order inserted into OrderDB: order_id=%s total_price=%.2f", order_id, normalized_total)
    except Exception as exc:
        conn.rollback()
        logger.error("Database error while creating order_id=%s: %s", order_id, exc, exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

    order_data = {
        "order_id": order_id,
        "restaurant_id": restaurant_id,
        "customer_id": customer_id,
        "items": items,
        "total_price": normalized_total,
        "status": status,
        "created_at": created_at,
    }
    publish_order_event(order_data)
    return order_data


@app.route("/health", methods=["GET"])
def health():
    dependencies_ready, error = check_order_dependencies()
    payload = {
        "status": "healthy" if dependencies_ready else "degraded",
        "service": "order-service",
        "dependencies_ready": dependencies_ready,
    }
    if error:
        payload["error"] = error
    return jsonify(payload), (200 if dependencies_ready else 503)


@app.route("/order", methods=["POST"])
def post_order():
    try:
        data = request.get_json() or {}
        order = create_order(
            restaurant_id=data.get("restaurant_id"),
            customer_id=data.get("customer_id"),
            items=data.get("items", []),
            total_price=data.get("total_price"),
        )
        return jsonify({"success": True, "order": order}), 201
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("Error creating order: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/orders", methods=["GET"])
def get_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT order_id, restaurant_id, customer_id, total_price, status, created_at
            FROM orders
            ORDER BY created_at DESC
            LIMIT 50;
            """
        )
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"count": len(orders), "orders": [dict(order) for order in orders]}), 200
    except Exception as exc:
        logger.error("Error fetching orders: %s", exc, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    ensure_rabbitmq_setup()
    app.run(host="0.0.0.0", port=5001, debug=False)
