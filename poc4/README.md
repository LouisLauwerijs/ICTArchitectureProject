# POC 4 — CQRS Reporting

## Technische vraag

> Hoe kunnen we complexe rapportages draaien (bijv. totale omzet per dag) **zonder de operationele besteldatabase te vertragen**?

## Wat dit bewijst

Dit POC bewijst dat je lees- en schrijfoperaties volledig kunt scheiden (CQRS — Command Query Responsibility Segregation):

- De **order-service** schrijft enkel naar de `order-db`. Hij weet niets af van rapporten.
- De **reporting-service** leest enkel uit de `reporting-db`. Hij raakt nooit de `order-db` aan voor rapportages.
- De `reporting-db` bevat een **geaggregeerd lees-model** (omzet per dag), dat veel sneller te bevragen is dan een `GROUP BY` over een grote ordertabel.
- De reporting-service synchroniseert dit model periodiek vanuit de `order-db` — in productie zou dit event-driven zijn (bijv. via RabbitMQ zoals in POC 1).
- De twee kanten kunnen **onafhankelijk schalen**: meer write-load → meer order-service replicas; meer report-queries → meer reporting-service replicas.

Dit is de kern van ADR-004 (CQRS voor rapportage).

## Architectuur

```
           WRITE SIDE                          READ SIDE
┌──────────────────────────┐        ┌──────────────────────────────┐
│  POST /orders            │        │  GET /report                 │
│  order-service           │──sync──│  reporting-service           │
│        │                 │        │        │                     │
│        ▼                 │        │        ▼                     │
│    order-db              │        │    reporting-db              │
│  (operationele data)     │        │  (geaggregeerd lees-model)   │
└──────────────────────────┘        └──────────────────────────────┘
```

De sync loopt elke 5 seconden (gesimuleerde event-trigger).

## Opstarten

### Stap 1 — Images bouwen (doe dit op de manager node)

```bash
docker build -t poc4-order-service ./order-service
docker build -t poc4-reporting-service ./reporting-service
```

> **Let op:** In een echte Swarm moet je de images beschikbaar maken op alle nodes.
> De makkelijkste manier voor dit POC is ze op elke node bouwen, of een lokale registry gebruiken (zie onderaan).

### Stap 2 — Stack deployen

```bash
docker stack deploy -f poc.yaml poc4
```

### Stap 3 — Wacht tot alles opstart (~20 seconden)

```bash
docker service logs poc4_order-service -f
docker service logs poc4_reporting-service -f
```

Je ziet eerst "Waiting for DB..." berichten, daarna "Connected" en "Schema ready".

### Stap 4 — Orders plaatsen (schrijf-kant)

```bash
# Plaats een paar bestellingen
curl -s -X POST http://localhost:3000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer":"Jan","item":"Pizza Margherita","amount":12.50}' | jq

curl -s -X POST http://localhost:3000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer":"Lien","item":"Pasta Carbonara","amount":14.00}' | jq

curl -s -X POST http://localhost:3000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer":"Pieter","item":"Tiramisu","amount":6.50}' | jq
```

### Stap 5 — Rapporten opvragen (lees-kant)

```bash
# Omzet per dag (uit de reporting-db, nooit uit de order-db)
curl -s http://localhost:3001/report | jq

# Totale omzet over alle dagen
curl -s http://localhost:3001/report/total | jq
```

Verwachte output:
```json
[
  {
    "day": "2026-05-15",
    "total_orders": 3,
    "total_revenue": "33.00",
    "last_synced_at": "2026-05-15T10:00:05.000Z"
  }
]
```

### Stap 6 — Isolatie aantonen

Je kunt de **reporting-service** zwaar belasten zonder dat de order-service er last van heeft:

```bash
# Stuur 50 report-queries tegelijk
for i in $(seq 1 50); do curl -s http://localhost:3001/report/total & done; wait
```

De `POST /orders` op poort 3000 blijft gewoon werken. De twee kanten interfereren niet.

### Opruimen

```bash
docker stack rm poc4
```

## Alternatief: lokale registry voor multi-node Swarm

Als je de stack op een echte Swarm met meerdere nodes uitvoert, moeten alle nodes de images kunnen pullen:

```bash
# Op de manager node:
docker service create --name registry --publish 5000:5000 registry:2

# Hernoem en push de images:
docker tag poc4-order-service localhost:5000/poc4-order-service
docker push localhost:5000/poc4-order-service

docker tag poc4-reporting-service localhost:5000/poc4-reporting-service
docker push localhost:5000/poc4-reporting-service
```

Pas daarna `poc.yaml` aan zodat de image-namen `localhost:5000/poc4-...` zijn.

## Gerelateerde ADR's

- **ADR-004** — CQRS voor rapportage: lees- en schrijfmodel scheiden