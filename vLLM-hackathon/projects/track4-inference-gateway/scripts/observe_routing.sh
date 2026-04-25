#!/bin/bash
# Tail gateway logs and print per-backend request counts from Prometheus metrics.
set -euo pipefail

GATEWAY_POD=$(kubectl get pod -n llm-d -l app=llm-d-gateway -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
if [ -z "${GATEWAY_POD}" ]; then
    echo "✗ No gateway pod found. Deploy first: bash scripts/deploy_gateway.sh"
    exit 1
fi

echo "Tailing gateway logs (Ctrl+C to stop). Metrics refresh every 5s."
echo ""

# Run log tail in the background
kubectl logs -n llm-d -f "$GATEWAY_POD" --tail=20 &
LOG_PID=$!
trap 'kill $LOG_PID 2>/dev/null' EXIT

while true; do
    echo ""
    echo "--- Per-backend request counts ($(date +%H:%M:%S)) ---"
    # Parse gateway /metrics via kubectl port-forward (assumed already running at :8000)
    curl -s http://localhost:8000/metrics 2>/dev/null | \
        grep '^llm_d_gateway_requests_total{' | \
        sed 's/llm_d_gateway_requests_total{backend="\([^"]*\)"} /  \1: /' || \
        echo "  (metrics not reachable — is port-forward running?)"
    sleep 5
done
