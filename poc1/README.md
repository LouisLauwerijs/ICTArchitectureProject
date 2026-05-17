# POC 1 — Inter-service Event Communication

## Technische vraag
Hoe garanderen we dat de Order-service en Payment-service **ontkoppeld** blijven terwijl ze toch een betrouwbare workflow doorlopen?

## Wat dit bewijst
- De Order-service weet niet dat de Payment-service bestaat — hij plaatst gewoon een bericht op de queue.
- De Payment-service weet niet hoe orders worden aangemaakt — hij luistert gewoon naar berichten.
- Als de Payment-service tijdelijk uitvalt, worden berichten **bewaard** in RabbitMQ en verwerkt zodra hij terug online is.
- Door `replicas: 2` op de payment-service zien we **load balancing** tussen twee workers.

## Architectuur

```
Order-service --> [RabbitMQ queue: order.created] --> Payment-service (x2)
   (producer)           (message broker)                  (consumers)
```

## Opstarten

Voer dit uit op de **manager node** van de Swarm, vanuit de `poc1` directory:

```bash
docker service create --name registry --publish 5000:5000 registry:2 && sleep 5 && docker build -t poc1-order-service ./order-service && docker build -t poc1-payment-service ./payment-service && docker tag poc1-order-service localhost:5000/poc1-order-service && docker tag poc1-payment-service localhost:5000/poc1-payment-service && docker push localhost:5000/poc1-order-service && docker push localhost:5000/poc1-payment-service && docker stack deploy -f poc.yaml poc
```

Wacht 30 seconden voor RabbitMQ volledig opgestart is, controleer dan:

```bash
docker service ls
```

Verwachte output:
```
ID    NAME                  REPLICAS   IMAGE
xxx   poc_rabbitmq          1/1        rabbitmq:3-management-alpine
xxx   poc_order-service     1/1        localhost:5000/poc1-order-service
xxx   poc_payment-service   2/2        localhost:5000/poc1-payment-service
```

## Logs bekijken

```bash
docker service logs poc_order-service -f
docker service logs poc_payment-service -f
```

Verwachte output:
```
[Order]   Published order #1 — €18.50 for Student 42
[Payment] ✓ Order #1 PAID — €18.50 charged to Student 42
[Payment] ✗ Order #2 FAILED — Payment gateway timeout  (wordt automatisch opnieuw geprobeerd)
```

## Decoupling aantonen

Stop de payment-service tijdelijk om te bewijzen dat orders niet verloren gaan:

```bash
docker service scale poc_payment-service=0 && sleep 15 && docker service scale poc_payment-service=2
```

Bekijk daarna de logs — alle orders die tijdens de downtime binnenkwamen worden meteen verwerkt:

```bash
docker service logs poc_payment-service -f
```

## Opruimen

```bash
docker stack rm poc && docker service rm registry
```

## Gerelateerde ADR's
- **ADR-001** — Asynchrone communicatie tussen Order en Payment
- **ADR-002** — RabbitMQ als message broker
