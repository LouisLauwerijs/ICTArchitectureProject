#!/bin/bash

set -euo pipefail

STACK_NAME="${STACK_NAME:-poc}"

docker build -t cqrs-order-service:latest ./order-service
docker build -t cqrs-reporting-service:latest ./reporting-service

if [ "$(docker info --format '{{.Swarm.LocalNodeState}}')" = "inactive" ]; then
  docker swarm init
fi

docker stack deploy -c poc.yaml "$STACK_NAME"
