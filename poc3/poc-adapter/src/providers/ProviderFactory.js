const DeliverooAdapter = require('../adapters/DeliverooAdapter');
const StuartAdapter = require('../adapters/StuartAdapter');

const PROVIDERS = {
  deliveroo: DeliverooAdapter,
  stuart: StuartAdapter,
};

function getProvider() {
  const providerName = (process.env.DELIVERY_PROVIDER || 'deliveroo').toLowerCase();
  const ProviderClass = PROVIDERS[providerName];

  if (!ProviderClass) {
    const available = Object.keys(PROVIDERS).join(', ');
    throw new Error(
      `Unknown provider "${providerName}". Available providers: ${available}`
    );
  }

  console.log(`[Factory] Using delivery provider: ${providerName}`);
  return new ProviderClass();
}

module.exports = { getProvider };
