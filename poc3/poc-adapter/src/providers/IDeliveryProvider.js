class IDeliveryProvider {
  /**
   * Dispatch a delivery order to the external provider.
   * @param {object} order - { orderId, pickupAddress, deliveryAddress }
   * @returns {object} - { trackingId, estimatedMinutes, provider }
   */
  async dispatch(order) {
    throw new Error(`dispatch() must be implemented by ${this.constructor.name}`);
  }

  /**
   * Get the current status of a dispatched order.
   * @param {string} trackingId
   * @returns {object} - { trackingId, status, location }
   */
  async getStatus(trackingId) {
    throw new Error(`getStatus() must be implemented by ${this.constructor.name}`);
  }

  /**
   * Cancel a dispatched order.
   * @param {string} trackingId
   * @returns {object} - { success, message }
   */
  async cancel(trackingId) {
    throw new Error(`cancel() must be implemented by ${this.constructor.name}`);
  }
}

module.exports = IDeliveryProvider;
