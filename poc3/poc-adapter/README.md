# POC: Multi-Provider Adapter

## Technische vraag

Hoe kunnen we van externe bezorgdienst wisselen (bijv. van Deliveroo naar Stuart) zonder de kernlogica van het systeem aan te passen?

## Wat bewijst deze POC?

Het Adapter-patroon (zie ADR-005) zorgt ervoor dat de Integration Service enkel communiceert via een vaste interne interface (`IDeliveryProvider`). De concrete implementatie per externe dienst zit volledig geïsoleerd in een eigen adapter. Een nieuwe provider toevoegen betekent één nieuwe klasse schrijven — geen enkele andere file hoeft te veranderen.

De switch tussen providers gebeurt via de omgevingsvariabele `DELIVERY_PROVIDER`. De rest van de applicatie merkt hier niets van.

## Structuur

```
src/
  providers/
    IDeliveryProvider.js     # Interne interface (contract)
    ProviderFactory.js       # Leest config, geeft juiste adapter terug
  adapters/
    DeliverooAdapter.js      # Adapter voor Deliveroo
    StuartAdapter.js         # Adapter voor Stuart
  index.js                   # Express API (Integration Service)
start.sh                     # Start script — deployt en stelt variabelen in
COMMANDO.md                  # Alle commando's voor testen en verdediging
```

## Opstarten

### Snelle manier — start.sh (aanbevolen)

```bash
docker build -t poc-adapter:latest .
chmod +x start.sh
source ./start.sh
```

Het script deployt de stack en wacht automatisch tot beide services klaar zijn. Daarna zijn `$DELIVEROO` en `$STUART` beschikbaar als variabelen in je terminal.

> Opmerking: `source` is verplicht zodat de variabelen beschikbaar blijven in je huidige terminal.

### Manuele manier (optioneel)

```bash
docker build -t poc-adapter:latest .
docker swarm init
docker stack deploy --compose-file poc.yaml poc
```

> Opmerking: op sommige Docker versies werkt `-f` niet als afkorting, gebruik dan `--compose-file`.

Wacht tot beide services `1/1` tonen:

```bash
docker stack services poc
```

Stel daarna de variabelen manueel in (of geef het ID zelf in op de plaats van de variabelen):

```bash
DELIVEROO=$(docker ps --filter name=poc_integration-deliveroo --format "{{.ID}}")
STUART=$(docker ps --filter name=poc_integration-stuart --format "{{.ID}}")
```

## Testen

> Opmerking: de poorten 3001 en 3002 zijn intern beschikbaar binnen het Docker Swarm netwerk. Testen gebeurt via `docker exec` rechtstreeks in de container.

### Dispatch een bestelling via Deliveroo

```bash
docker exec $DELIVEROO wget -qO- \
  --post-data='{"orderId":"ORD-001","pickupAddress":"Grote Markt 1, Brussel","deliveryAddress":"Naamsestraat 22, Leuven"}' \
  --header='Content-Type: application/json' \
  http://localhost:3000/dispatch
```

Verwacht resultaat:
```json
{"trackingId":"DLV-ORD-001-...","estimatedMinutes":25,"provider":"Deliveroo"}
```

### Dispatch dezelfde bestelling via Stuart

```bash
docker exec $STUART wget -qO- \
  --post-data='{"orderId":"ORD-001","pickupAddress":"Grote Markt 1, Brussel","deliveryAddress":"Naamsestraat 22, Leuven"}' \
  --header='Content-Type: application/json' \
  http://localhost:3000/dispatch
```

Verwacht resultaat:
```json
{"trackingId":"STU-ORD-001-...","estimatedMinutes":20,"provider":"Stuart"}
```

### Status opvragen

Vervang `<trackingId>` door de waarde uit de dispatch respons. (dit moet bij opvragen en annuleren)

```bash
# Via Deliveroo
docker exec $DELIVEROO wget -qO- http://localhost:3000/status/DLV-ORD-001-123

# Via Stuart
docker exec $STUART wget -qO- http://localhost:3000/status/STU-ORD-001-123
```

### Bestelling annuleren

```bash
# Via Deliveroo
docker exec $DELIVEROO wget -qO- --method=DELETE http://localhost:3000/cancel/DLV-ORD-001-123

# Via Stuart
docker exec $STUART wget -qO- --method=DELETE http://localhost:3000/cancel/STU-ORD-001-123
```

### Health check

```bash
docker exec $DELIVEROO wget -qO- http://localhost:3000/health
docker exec $STUART wget -qO- http://localhost:3000/health
```

## Stack verwijderen

```bash
docker stack rm poc
```

## Wat je ziet

Beide services draaien dezelfde code (`poc-adapter:latest`). Het enige verschil is de omgevingsvariabele `DELIVERY_PROVIDER`. De responses tonen een andere provider-naam, een andere tracking ID prefix en andere geschatte levertijden — zonder dat de API of de kernlogica aangepast werd.

Dit bewijst dat het Adapter-patroon werkt zoals beschreven in ADR-005.
