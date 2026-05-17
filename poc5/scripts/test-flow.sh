#!/bin/bash

set -euo pipefail

ORDER_SERVICE_URL="${ORDER_SERVICE_URL:-http://localhost:5001}"
REPORTING_SERVICE_URL="${REPORTING_SERVICE_URL:-http://localhost:5002}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-20}"

echo "============================================================"
echo "  CQRS Reporting PoC - End-to-End Test"
echo "============================================================"
echo

for dependency in curl jq; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    echo "Missing required dependency: $dependency"
    exit 1
  fi
done

echo "Dependencies found: curl, jq"
echo

require_healthy() {
  local service_name="$1"
  local url="$2"
  local status

  status="$(curl -fsS "$url/health" | jq -r '.status')"
  if [ "$status" != "healthy" ]; then
    echo "$service_name is not healthy (status=$status)"
    exit 1
  fi
}

fetch_json() {
  curl -fsS "$1"
}

place_order() {
  local payload="$1"
  local response
  local success
  local order_id

  response="$(curl -fsS -X POST "$ORDER_SERVICE_URL/order" -H "Content-Type: application/json" -d "$payload")"
  success="$(echo "$response" | jq -r '.success')"
  order_id="$(echo "$response" | jq -r '.order.order_id // empty')"

  if [ "$success" != "true" ] || [ -z "$order_id" ]; then
    echo "Order creation failed:"
    echo "$response" | jq '.'
    exit 1
  fi

  echo "$response"
}

wait_for_reports() {
  local expected_events="$1"
  local deadline=$((SECONDS + MAX_WAIT_SECONDS))

  while [ "$SECONDS" -lt "$deadline" ]; do
    local revenue_json
    local restaurant_json
    local status_json
    local event_log_json
    local revenue_count
    local restaurant_count
    local placed_count
    local event_log_count

    revenue_json="$(fetch_json "$REPORTING_SERVICE_URL/reports/revenue-by-day")"
    restaurant_json="$(fetch_json "$REPORTING_SERVICE_URL/reports/revenue-by-restaurant")"
    status_json="$(fetch_json "$REPORTING_SERVICE_URL/reports/order-status-summary")"
    event_log_json="$(fetch_json "$REPORTING_SERVICE_URL/reports/event-log")"

    revenue_count="$(echo "$revenue_json" | jq -r '.count')"
    restaurant_count="$(echo "$restaurant_json" | jq -r '.count')"
    placed_count="$(echo "$status_json" | jq -r '[.data[] | select(.status == "placed")][0].count // 0')"
    event_log_count="$(echo "$event_log_json" | jq -r '.count')"

    if [ "$revenue_count" -ge 1 ] && [ "$restaurant_count" -ge 2 ] && [ "$placed_count" -ge "$expected_events" ] && [ "$event_log_count" -ge "$expected_events" ]; then
      echo "$revenue_json"
      return 0
    fi

    sleep 1
  done

  echo "Timed out waiting for ReportingDB to contain processed events"
  return 1
}

echo "Checking service health..."
require_healthy "Order Service" "$ORDER_SERVICE_URL"
require_healthy "Reporting Service" "$REPORTING_SERVICE_URL"

consumer_running="$(fetch_json "$REPORTING_SERVICE_URL/health" | jq -r '.event_consumer_running')"
if [ "$consumer_running" != "true" ]; then
  echo "Reporting Service is healthy but event_consumer_running=$consumer_running"
  exit 1
fi

echo "Order Service is healthy"
echo "Reporting Service is healthy"
echo "Reporting event consumer is running"
echo

echo "Placing first order..."
ORDER_1="$(place_order '{
  "restaurant_id": 1,
  "customer_id": 100,
  "items": [
    {"name": "Pizza Margherita", "price": 12.00},
    {"name": "Coca-Cola", "price": 2.50}
  ],
  "total_price": 14.50
}')"
ORDER_ID_1="$(echo "$ORDER_1" | jq -r '.order.order_id')"
echo "Order 1 created: $ORDER_ID_1"

echo "Placing second order..."
ORDER_2="$(place_order '{
  "restaurant_id": 2,
  "customer_id": 200,
  "items": [
    {"name": "Burger King", "price": 9.99},
    {"name": "Fries", "price": 2.99}
  ],
  "total_price": 12.98
}')"
ORDER_ID_2="$(echo "$ORDER_2" | jq -r '.order.order_id')"
echo "Order 2 created: $ORDER_ID_2"
echo

echo "Waiting for ReportingDB to be updated..."
REVENUE_REPORT="$(wait_for_reports 2)" || {
  echo
  echo "Revenue report:"
  fetch_json "$REPORTING_SERVICE_URL/reports/revenue-by-day" | jq '.'
  echo
  echo "Restaurant report:"
  fetch_json "$REPORTING_SERVICE_URL/reports/revenue-by-restaurant" | jq '.'
  echo
  echo "Status report:"
  fetch_json "$REPORTING_SERVICE_URL/reports/order-status-summary" | jq '.'
  echo
  echo "Event log:"
  fetch_json "$REPORTING_SERVICE_URL/reports/event-log" | jq '.'
  exit 1
}

RESTAURANT_REPORT="$(fetch_json "$REPORTING_SERVICE_URL/reports/revenue-by-restaurant")"
STATUS_REPORT="$(fetch_json "$REPORTING_SERVICE_URL/reports/order-status-summary")"
EVENT_LOG="$(fetch_json "$REPORTING_SERVICE_URL/reports/event-log")"
ORDERS_FROM_DB="$(fetch_json "$ORDER_SERVICE_URL/orders")"

echo
echo "Revenue by day:"
echo "$REVENUE_REPORT" | jq '.'
echo
echo "Revenue by restaurant:"
echo "$RESTAURANT_REPORT" | jq '.'
echo
echo "Order status summary:"
echo "$STATUS_REPORT" | jq '.'
echo
echo "Event log:"
echo "$EVENT_LOG" | jq '.'
echo
echo "Orders from OrderDB:"
echo "$ORDERS_FROM_DB" | jq '.orders[] | {order_id, restaurant_id, total_price}'

today_order_count="$(echo "$REVENUE_REPORT" | jq -r '.data[0].order_count')"
today_total_revenue="$(echo "$REVENUE_REPORT" | jq -r '.data[0].total_revenue')"
event_log_count="$(echo "$EVENT_LOG" | jq -r '.count')"

if [ "$today_order_count" -lt 2 ]; then
  echo "Expected at least 2 orders in revenue_per_day, got $today_order_count"
  exit 1
fi

if [ "$event_log_count" -lt 2 ]; then
  echo "Expected at least 2 rows in event_log, got $event_log_count"
  exit 1
fi

echo
echo "============================================================"
echo "CQRS flow verified with real ReportingDB data"
echo "============================================================"
echo "Order 1: $ORDER_ID_1"
echo "Order 2: $ORDER_ID_2"
echo "Orders processed today: $today_order_count"
echo "Total revenue today: $today_total_revenue"
