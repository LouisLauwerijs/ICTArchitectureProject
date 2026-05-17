# PoC 5 - CQRS Reporting

Deze proof of concept toont hoe rapportage losgekoppeld kan worden van de operationele bestelstroom.
De `order-service` schrijft bestellingen naar `OrderDB` en publiceert `order.placed` events via RabbitMQ.
De `reporting-service` consumeert die events en bouwt een aparte `ReportingDB` op met read models voor rapportage.

## Structuur

```text
poc5/
├── README.md
├── poc.yaml
├── docker-compose.yml
├── order-service/
├── reporting-service/
└── scripts/
```

## Read models

- `revenue_per_day`
- `orders_per_restaurant`
- `order_status_summary`
- `event_log`

## Lokaal testen

Voor lokale verificatie kan de compose-opstelling gebruikt worden:

```bash
docker compose down -v
docker compose up -d --build
```

Plaats daarna testdata:

```bash
bash scripts/test-flow.sh
```

## Docker Swarm

Voor Swarm worden eerst de twee service-images gebouwd:

```bash
docker build -t cqrs-order-service:latest ./order-service
docker build -t cqrs-reporting-service:latest ./reporting-service
```

Initialiseer Swarm indien nodig en deploy de stack:

```bash
docker swarm init
docker stack deploy -c poc.yaml poc
```

Controle:

```bash
docker stack services poc
docker stack ps poc
docker service logs poc_order-service
docker service logs poc_reporting-service
```

Daarna kan opnieuw getest worden via:

```bash
bash scripts/test-flow.sh
```

## Verwachte uitkomst

Na het plaatsen van orders moet:

- `OrderDB` bestellingen bevatten
- RabbitMQ de events doorgeven aan de reporting consumer
- `ReportingDB` gevuld worden
- de rapportage-endpoints data teruggeven

## Belangrijke endpoints

- `POST /order`
- `GET /orders`
- `GET /health`
- `GET /reports/revenue-by-day`
- `GET /reports/revenue-by-restaurant`
- `GET /reports/order-status-summary`
- `GET /reports/event-log`
