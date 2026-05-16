#!/usr/bin/env bash
set -euo pipefail
MANAGER_IP=$(docker node inspect self --format '{{ .Status.Addr }}')
REGISTRY="${MANAGER_IP}"
sed -i "s|127.0.0.1:5000|${REGISTRY}|g" poc.yaml
echo "▶ Ensuring local registry is running…"
docker service ls --filter name=poc_registry --quiet | grep -q . \
  || docker service create --name poc_registry --publish 5000:5000 --constraint 'node.role == manager' registry:2
echo "  registry OK"
echo ""
echo "▶ Building images…"
docker build --network=host -t "${REGISTRY}/poc-tracking-ws-server:latest" ./ws-server
docker build --network=host -t "${REGISTRY}/poc-tracking-sim:latest" ./tracker-sim
docker build --network=host -t "${REGISTRY}/poc-tracking-client:latest" ./client
echo ""
echo "▶ Pushing images to ${REGISTRY}…"
docker push "${REGISTRY}/poc-tracking-ws-server:latest"
docker push "${REGISTRY}/poc-tracking-sim:latest"
docker push "${REGISTRY}/poc-tracking-client:latest"
echo ""
echo "✔ All images pushed. You can now run:"
echo "    docker stack deploy -f poc.yaml poc"

