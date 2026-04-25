#!/bin/bash
# Shift weighted traffic between v1 and v2 without redeploying.
# Usage: bash shift_traffic.sh <v1-weight> <v2-weight>
#   e.g. bash shift_traffic.sh 50 50        # 50/50 split
#        bash shift_traffic.sh 0 100        # full cutover to v2
#        bash shift_traffic.sh 100 0        # instant rollback to v1
set -euo pipefail

V1_WEIGHT="${1:?Usage: $0 <v1-weight> <v2-weight>}"
V2_WEIGHT="${2:?Usage: $0 <v1-weight> <v2-weight>}"

PATCH=$(cat <<EOF
{
  "spec": {
    "values": {
      "gateway": {
        "routes": [{
          "name": "llama-8b-canary-route",
          "match": {"model": "meta-llama/Llama-3.1-8B-Instruct"},
          "weightedBackends": [
            {"backend": "llama-8b-v1", "weight": ${V1_WEIGHT}},
            {"backend": "llama-8b-v2", "weight": ${V2_WEIGHT}}
          ]
        }]
      }
    }
  }
}
EOF
)

# If the gateway is a HelmRelease (flux/argo), patch that; otherwise re-run helm upgrade
# with an inline override. Try HelmRelease first.
if kubectl get helmrelease -n llm-d llm-d >/dev/null 2>&1; then
    kubectl patch helmrelease -n llm-d llm-d --type merge -p "$PATCH"
    echo "✓ Patched HelmRelease. Weights: v1=${V1_WEIGHT}% v2=${V2_WEIGHT}%"
else
    # Fall back to helm upgrade with --set
    helm upgrade llm-d /workspace/llm-d/charts/llm-d \
        --namespace llm-d \
        --reuse-values \
        --set "gateway.routes[0].weightedBackends[0].weight=${V1_WEIGHT}" \
        --set "gateway.routes[0].weightedBackends[1].weight=${V2_WEIGHT}" \
        --wait --timeout 120s
    echo "✓ Shifted traffic: v1=${V1_WEIGHT}% v2=${V2_WEIGHT}%"
fi

echo ""
echo "Verify by sending traffic:"
echo "  python3 scripts/send_mixed_traffic.py --ab-split -n 100"
