const IDeliveryProvider = require('../providers/IDeliveryProvider');

class StuartAdapter extends IDeliveryProvider {
  constructor() {
    super();
    this.providerName = 'Stuart';
  }

  async dispatch(order) {
    console.log(`[Stuart] Creating job for order ${order.orderId}...`);

    await this._simulateNetworkDelay();

    const trackingId = `STU-${order.orderId}-${Date.now()}`;
    console.log(`[Stuart] Job created. Tracking ID: ${trackingId}`);

    return {
      trackingId,
      estimatedMinutes: 20,
      provider: this.providerName,
    };
  }

  async getStatus(trackingId) {
    console.log(`[Stuart] Fetching job status for ${trackingId}...`);
    await this._simulateNetworkDelay();

    return {
      trackingId,
      status: 'PICKING_UP',
      location: 'Naamsestraat 10, Leuven',
      provider: this.providerName,
    };
  }

  async cancel(trackingId) {
    console.log(`[Stuart] Cancelling job ${trackingId}...`);
    await this._simulateNetworkDelay();

    return {
      success: true,
      message: `Stuart job ${trackingId} has been cancelled.`,
      provider: this.providerName,
    };
  }

  async _simulateNetworkDelay() {
    return new Promise((resolve) => setTimeout(resolve, 80));
  }
}

module.exports = StuartAdapter;
