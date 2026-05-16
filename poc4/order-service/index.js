const mysql = require("mysql2/promise");
const express = require("express");

const DB_HOST = process.env.DB_HOST || "order-db";
const DB_USER = process.env.DB_USER || "root";
const DB_PASS = process.env.DB_PASS || "secret";
const DB_NAME = process.env.DB_NAME || "orders";

const app = express();
app.use(express.json());

let db;

async function connectDb(retries = 15) {
  for (let i = 0; i < retries; i++) {
    try {
      db = await mysql.createConnection({
        host: DB_HOST,
        user: DB_USER,
        password: DB_PASS,
        database: DB_NAME,
      });
      console.log("[Order] Connected to order-db");
      return;
    } catch (err) {
      console.log(`[Order] Waiting for order-db... (${i + 1}/${retries})`);
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
  throw new Error("Could not connect to order-db");
}

async function setupSchema() {
  await db.execute(`
    CREATE TABLE IF NOT EXISTS orders (
      id INT AUTO_INCREMENT PRIMARY KEY,
      customer VARCHAR(100) NOT NULL,
      item VARCHAR(100) NOT NULL,
      amount DECIMAL(10,2) NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);
  console.log("[Order] Schema ready");
}

app.post("/orders", async (req, res) => {
  const { customer, item, amount } = req.body;
  if (!customer || !item || !amount) {
    return res.status(400).json({ error: "customer, item and amount are required" });
  }

  const [result] = await db.execute(
    "INSERT INTO orders (customer, item, amount) VALUES (?, ?, ?)",
    [customer, item, parseFloat(amount)]
  );

  const order = { id: result.insertId, customer, item, amount: parseFloat(amount) };
  console.log(`[Order] ✓ New order #${order.id} — ${customer} ordered ${item} for €${amount}`);

  res.status(201).json(order);
});

app.get("/orders", async (req, res) => {
  const [rows] = await db.execute("SELECT * FROM orders ORDER BY created_at DESC");
  res.json(rows);
});

async function main() {
  await connectDb();
  await setupSchema();
  app.listen(3000, () => console.log("[Order] Listening on :3000"));
}

main().catch(console.error);