-- ReportingDB Schema (Read-Side)
-- Gedenormaliseerde, read-optimized tabellen gevoed door event-consumers

-- Dagelijks inkomsten rapport
CREATE TABLE IF NOT EXISTS revenue_per_day (
    date DATE PRIMARY KEY,
    total_revenue DECIMAL(12, 2) NOT NULL DEFAULT 0,
    order_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_revenue_per_day_date ON revenue_per_day(date);

-- Inkomsten per restaurant
CREATE TABLE IF NOT EXISTS orders_per_restaurant (
    restaurant_id INTEGER PRIMARY KEY,
    order_count INTEGER NOT NULL DEFAULT 0,
    total_revenue DECIMAL(12, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_per_restaurant_id ON orders_per_restaurant(restaurant_id);

-- Status samenvatting
CREATE TABLE IF NOT EXISTS order_status_summary (
    status VARCHAR(50) PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event log (audit trail)
CREATE TABLE IF NOT EXISTS event_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    order_id VARCHAR(50),
    processed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_event_log_order_id ON event_log(order_id);
CREATE INDEX IF NOT EXISTS idx_event_log_processed_at ON event_log(processed_at);
