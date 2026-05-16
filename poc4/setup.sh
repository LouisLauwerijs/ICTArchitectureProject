#!/bin/bash
set -e

echo "=== Nodes in deze swarm ==="
docker node ls
echo ""

read -p "Geef de node-naam voor order-db: " ORDER_NODE
read -p "Geef de node-naam voor reporting-db: " REPORTING_NODE

docker node update --label-add db=order "$ORDER_NODE"
echo "[OK] Label db=order gezet op $ORDER_NODE"

docker node update --label-add db=reporting "$REPORTING_NODE"
echo "[OK] Label db=reporting gezet op $REPORTING_NODE"

echo ""
echo "=== Images bouwen ==="
docker build -t poc4-order-service ./order-service
docker build -t poc4-reporting-service ./reporting-service

echo ""
echo "=== Stack deployen ==="
docker stack deploy --compose-file poc.yaml poc4

echo ""
echo "=== Klaar! ==="
echo "Logs order-service:     docker service logs poc4_order-service -f"
echo "Logs reporting-service: docker service logs poc4_reporting-service -f"
echo "Order plaatsen:         curl -s -X POST http://localhost:3000/orders -H 'Content-Type: application/json' -d '{\"customer\":\"Jan\",\"item\":\"Pizza\",\"amount\":12.50}' | jq"
echo "Rapport opvragen:       curl -s http://localhost:3001/report | jq"
echo "Totaal opvragen:        curl -s http://localhost:3001/report/total | jq"