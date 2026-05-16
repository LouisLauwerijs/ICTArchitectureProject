#!/bin/bash

docker stack deploy --compose-file poc.yaml poc

echo "Wachten tot services opstarten..."
while true; do
  READY=$(docker stack services poc --format "{{.Replicas}}" | grep -c "1/1")
  if [ "$READY" -eq 2 ]; then
    break
  fi
  echo "Nog niet klaar, even wachten..."
  sleep 3
done

export DELIVEROO=$(docker ps --filter name=poc_integration-deliveroo --format "{{.ID}}")
export STUART=$(docker ps --filter name=poc_integration-stuart --format "{{.ID}}")

echo ""
echo "Services zijn klaar!"
echo "Deliveroo container: $DELIVEROO"
echo "Stuart container:    $STUART"
echo ""
echo "Je kan nu testen met \$DELIVEROO en \$STUART"
