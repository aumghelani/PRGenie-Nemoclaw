#!/bin/bash
# =============================================================================
# Infinite Scale — Full Deployment Pipeline
#
# Deploys the complete disaggregated inference stack:
#   1. kind Kubernetes cluster with GPU support
#   2. Prometheus monitoring stack
#   3. llm-d with disaggregated prefill/decode configuration
#   4. Autoscaling policies
#
# Prerequisites: Tier 3 Brev instance (4x A100)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLUSTER_NAME="llm-d-hackathon"
NAMESPACE="llm-d"
VALUES_FILE="${VALUES_FILE:-/workspace/llm-d-configs/values-70b-distributed.yaml}"

echo "============================================="
echo "  Infinite Scale — Deployment Pipeline"
echo "  Cluster: $CLUSTER_NAME"
echo "  Namespace: $NAMESPACE"
echo "============================================="

# --- Step 1: Create Kubernetes cluster ---
echo ""
echo "[1/5] Creating kind cluster..."

if kind get clusters 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    echo "  Cluster '$CLUSTER_NAME' already exists. Reusing."
else
    cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ${CLUSTER_NAME}
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: ClusterConfiguration
    apiServer:
      extraArgs:
        "enable-admission-plugins": "ResourceQuota"
- role: worker
  extraMounts:
  - hostPath: /models
    containerPath: /models
    readOnly: true
- role: worker
  extraMounts:
  - hostPath: /models
    containerPath: /models
    readOnly: true
EOF
    echo "  Cluster created."
fi

kubectl cluster-info --context "kind-${CLUSTER_NAME}"

# --- Step 2: Install NVIDIA device plugin ---
echo ""
echo "[2/5] Installing NVIDIA GPU device plugin..."
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/deployments/static/nvidia-device-plugin.yml
echo "  Waiting for device plugin to be ready..."
kubectl -n kube-system rollout status daemonset/nvidia-device-plugin-daemonset --timeout=120s 2>/dev/null || true

# --- Step 3: Deploy Prometheus monitoring ---
echo ""
echo "[3/5] Deploying Prometheus monitoring stack..."
kubectl create namespace monitoring 2>/dev/null || true

# Deploy a lightweight Prometheus via Helm
if helm list -n monitoring 2>/dev/null | grep -q prometheus; then
    echo "  Prometheus already deployed. Skipping."
else
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
    helm repo update
    helm install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --set grafana.enabled=false \
        --set alertmanager.enabled=false \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --wait --timeout 180s
    echo "  Prometheus deployed."
fi

# Apply custom metrics rules
kubectl apply -f "${SCRIPT_DIR}/prometheus-rules.yaml" -n monitoring

# --- Step 4: Deploy llm-d ---
echo ""
echo "[4/5] Deploying llm-d with disaggregated serving..."
kubectl create namespace "$NAMESPACE" 2>/dev/null || true

cd /workspace/llm-d
if helm list -n "$NAMESPACE" 2>/dev/null | grep -q llm-d; then
    echo "  Upgrading existing llm-d deployment..."
    helm upgrade llm-d ./charts/llm-d \
        -f "$VALUES_FILE" \
        --namespace "$NAMESPACE" \
        --wait --timeout 300s
else
    helm install llm-d ./charts/llm-d \
        -f "$VALUES_FILE" \
        --namespace "$NAMESPACE" \
        --wait --timeout 300s
fi

echo "  Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=llm-d -n "$NAMESPACE" --timeout=300s 2>/dev/null || true

# --- Step 5: Apply autoscaling policies ---
echo ""
echo "[5/5] Applying autoscaling policies..."
kubectl apply -f "${SCRIPT_DIR}/autoscale-policy.yaml" -n "$NAMESPACE"

# --- Summary ---
echo ""
echo "============================================="
echo "  Deployment complete!"
echo ""
echo "  Pods:"
kubectl get pods -n "$NAMESPACE" 2>/dev/null || echo "  (waiting for pods to start)"
echo ""
echo "  Access the gateway:"
echo "    kubectl port-forward -n $NAMESPACE svc/llm-d-gateway 8000:8000 &"
echo "    curl http://localhost:8000/v1/models"
echo ""
echo "  Monitor with k9s:"
echo "    k9s -n $NAMESPACE"
echo ""
echo "  Prometheus metrics:"
echo "    kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 &"
echo ""
echo "  Next: python3 load_test.py"
echo "============================================="
