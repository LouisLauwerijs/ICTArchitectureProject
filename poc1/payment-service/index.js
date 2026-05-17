const amqp = require("amqplib");

const RABBITMQ_URL = process.env.RABBITMQ_URL || "amqp://guest:guest@rabbitmq:5672";
const QUEUE = "order.created";

async function connect(retries = 10) {
  for (let i = 0; i < retries; i++) {
    try {
      const conn = await amqp.connect(RABBITMQ_URL);
      console.log("[Payment] Connected to RabbitMQ");
      return conn;
    } catch (err) {
      console.log(`[Payment] Waiting for RabbitMQ... (${i + 1}/${retries})`);
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
  throw new Error("Could not connect to RabbitMQ");
}

async function processPayment(order) {
  await new Promise((r) => setTimeout(r, 500));
  if (Math.random() < 0.1) {
    throw new Error("Payment gateway timeout");
  }
  return { status: "PAID", chargedAmount: order.total };
}

async function main() {
  const conn = await connect();
  const channel = await conn.createChannel();
  await channel.assertQueue(QUEUE, { durable: true });
  channel.prefetch(1);

  console.log("[Payment] Waiting for orders...");

  channel.consume(QUEUE, async (msg) => {
    if (!msg) return;
    const order = JSON.parse(msg.content.toString());
    console.log(`[Payment] Received order #${order.orderId} — processing payment of €${order.total}...`);
    try {
      const result = await processPayment(order);
      console.log(`[Payment] ✓ Order #${order.orderId} PAID — €${result.chargedAmount} charged to ${order.customer}`);
      channel.ack(msg);
    } catch (err) {
      console.error(`[Payment] ✗ Order #${order.orderId} FAILED — ${err.message}`);
      channel.nack(msg, false, true);
    }
  });
}

main().catch(console.error);