const amqp = require("amqplib");

const RABBITMQ_URL = process.env.RABBITMQ_URL || "amqp://guest:guest@rabbitmq:5672";
const QUEUE = "order.created";

async function connect(retries = 10) {
  for (let i = 0; i < retries; i++) {
    try {
      const conn = await amqp.connect(RABBITMQ_URL);
      console.log("[Order] Connected to RabbitMQ");
      return conn;
    } catch (err) {
      console.log(`[Order] Waiting for RabbitMQ... (${i + 1}/${retries})`);
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
  throw new Error("Could not connect to RabbitMQ");
}

async function main() {
  const conn = await connect();
  const channel = await conn.createChannel();
  await channel.assertQueue(QUEUE, { durable: true });

  let orderId = 1;
  setInterval(() => {
    const order = {
      orderId: orderId++,
      customer: "Student " + Math.floor(Math.random() * 100),
      items: ["Pizza Margherita", "Cola"],
      total: (Math.random() * 30 + 5).toFixed(2),
      timestamp: new Date().toISOString(),
    };
    const msg = JSON.stringify(order);
    channel.sendToQueue(QUEUE, Buffer.from(msg), { persistent: true });
    console.log(`[Order] Published order #${order.orderId} — €${order.total} for ${order.customer}`);
  }, 5000);
}

main().catch(console.error);