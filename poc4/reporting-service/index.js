const mysql = require("mysql2/promise");
const express = require("express");

const ORDER_DB_HOST = process.env.ORDER_DB_HOST || "order-db";
const REPORT_DB_HOST = process.env.REPORT_DB_HOST || "reporting-db";
const DB_USER = process.env.DB_USER || "root";
const DB_PASS = process.env.DB_PASS || "secret";

const app = express();

let orderDb;
let reportDb;

async function connectDb(host, retries = 15) {
  for (let i = 0; i < retries; i++) {
    try {
      const conn = await mysql.createConnection({
        host,
        user: DB_USER,
        password: DB_PASS,
        database: host === ORDER_DB_HOST ? "orders" : "reporting",
      });
      console.log(`[Reporting] Connected to ${host}`);
      return conn;
    } catch (err) {
      console.log(`[Reporting] Waiting for ${host}... (${i + 1}/${retries})`);
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
  throw new Error(`Could not connect to ${host}`);
}

async function setupSchema() {
  await reportDb.execute(`
    CREATE TABLE IF NOT EXISTS daily_revenue (
      day DATE PRIMARY KEY,
      total_orders INT NOT NULL DEFAULT 0,
      total_revenue DECIMAL(12,2) NOT NULL DEFAULT 0.00,
      last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
  `);
  console.log("[Reporting] Schema ready");
}

async function syncReportingDb() {
  const [rows] = await orderDb.execute(`
    SELECT
      DATE(created_at) AS day,
      COUNT(*)         AS total_orders,
      SUM(amount)      AS total_revenue
    FROM orders
    GROUP BY DATE(created_at)
  `);

  for (const row of rows) {
    await reportDb.execute(
      `INSERT INTO daily_revenue (day, total_orders, total_revenue)
       VALUES (?, ?, ?)
       ON DUPLICATE KEY UPDATE
         total_orders   = VALUES(total_orders),
         total_revenue  = VALUES(total_revenue),
         last_synced_at = NOW()`,
      [row.day, row.total_orders, row.total_revenue]
    );
  }

  if (rows.length > 0) {
    console.log(`[Reporting] Synced ${rows.length} day(s) into reporting-db`);
  }
}

app.get("/report", async (req, res) => {
  const [rows] = await reportDb.execute(
    "SELECT * FROM daily_revenue ORDER BY day DESC"
  );
  res.json(rows);
});

app.get("/report/total", async (req, res) => {
  const [rows] = await reportDb.execute(`
    SELECT
      SUM(total_orders)   AS total_orders,
      SUM(total_revenue)  AS total_revenue,
      MIN(day)            AS since,
      MAX(last_synced_at) AS last_synced_at
    FROM daily_revenue
  `);
  res.json(rows[0]);
});

async function main() {
  orderDb = await connectDb(ORDER_DB_HOST);
  reportDb = await connectDb(REPORT_DB_HOST);
  await setupSchema();

  setInterval(syncReportingDb, 5000);
  await syncReportingDb();

  app.listen(3001, () => console.log("[Reporting] Listening on :3001"));
}

main().catch(console.error);