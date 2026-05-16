const IDeliveryProvider = require('../providers/IDeliveryProvider');

class DeliverooAdapter extends IDeliveryProvider {
  constructor() {
    super();
    this.providerName = 'Deliveroo';
  }

  async dispatch(order) {
    console.log(`[Deliveroo] Dispatching order ${order.orderId}...`);

    await this._simulateNetworkDelay();

    const trackingId = `DLV-${order.orderId}-${Date.now()}`;
    console.log(`[Deliveroo] Order dispatched. Tracking ID: ${trackingId}`);

    return {
      trackingId,
      estimatedMinutes: 25,
      provider: this.providerName,
    };
  }

  async getStatus(trackingId) {
    console.log(`[Deliveroo] Fetching status for ${trackingId}...`);
    await this._simulateNetworkDelay();

    return {
      trackingId,
      status: 'IN_TRANSIT',
      location: 'Brusselsesteenweg 42, Leuven',
      provider: this.providerName,
    };
  }

  async cancel(trackingId) {
    console.log(`[Deliveroo] Cancelling order ${trackingId}...`);
    await this._simulateNetworkDelay();

    return {
      success: true,
      message: `Deliveroo order ${trackingId} has been cancelled.`,
      provider: this.providerName,
    };
  }

  async _simulateNetworkDelay() {
    return new Promise((resolve) => setTimeout(resolve, 100));
  }
}

module.exports = DeliverooAdapter;
