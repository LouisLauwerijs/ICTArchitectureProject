const express = require('express');
const { getProvider } = require('./providers/ProviderFactory');

const app = express();
app.use(express.json());

const provider = getProvider();

// POST /dispatch
// Body: { orderId, pickupAddress, deliveryAddress }
app.post('/dispatch', async (req, res) => {
  const { orderId, pickupAddress, deliveryAddress } = req.body;

  if (!orderId || !pickupAddress || !deliveryAddress) {
    return res.status(400).json({ error: 'orderId, pickupAddress and deliveryAddress are required.' });
  }

  try {
    const result = await provider.dispatch({ orderId, pickupAddress, deliveryAddress });
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /status/:trackingId
app.get('/status/:trackingId', async (req, res) => {
  try {
    const result = await provider.getStatus(req.params.trackingId);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE /cancel/:trackingId
app.delete('/cancel/:trackingId', async (req, res) => {
  try {
    const result = await provider.cancel(req.params.trackingId);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /health
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', provider: process.env.DELIVERY_PROVIDER || 'deliveroo' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`[Integration Service] Listening on port ${PORT}`);
});
