# Track 4 Builder — llm-d Inference Gateway: Multi-Model & A/B Routing

Reference project for the Track 4 **Inference at Scale** Builder lane. The official page says:

> **Multi-model deployment** with intelligent routing and autoscaling policies. Configure **traffic splitting and A/B model comparison** in production.

The existing `projects/advanced-infinite-scale/` covers single-model disaggregated serving (Track 4 Deep Tech). This kit covers the **Builder** middle lane: two models side-by-side behind one gateway, with weighted A/B traffic splits you can shift from a single kubectl command.

## What's here

```
README.md                           # This file
helm-values/
  values-multi-model.yaml           # Two distinct models (8B + 8B-Instruct-FP8) on one gateway
  values-ab-split.yaml              # Canary deploy: 80% v1, 20% v2 of the same model
  values-model-pool-hpa.yaml        # HorizontalPodAutoscaler policies per model pool
scripts/
  deploy_gateway.sh                 # Helm install + verify
  send_mixed_traffic.py             # Drive the gateway with labeled requests to show routing
  shift_traffic.sh                  # Kubectl patch to move weights at runtime
  observe_routing.sh                # Tail gateway logs + print per-backend request counts
```

## Why this matters

Every serious inference deployment needs to answer three questions:

1. **How do I serve multiple models behind one endpoint?** (Different customers, different model variants.)
2. **How do I roll out a new model version safely?** (Canary traffic shifts without downtime.)
3. **How do I scale each model independently based on its own load?** (Model A is busy; model B is idle — autoscale each pool.)

The llm-d Inference Gateway solves all three. This kit demonstrates each concretely.

## Quick start

Requires a running Kubernetes cluster with GPU nodes. On a Brev Tier 3 instance, create one via the existing script:

```bash
bash /workspace/scripts/start_kind_cluster.sh
```

Then deploy the multi-model gateway:

```bash
cd projects/track4-inference-gateway
bash scripts/deploy_gateway.sh helm-values/values-multi-model.yaml
```

This stands up:

- `llama-8b-pool` — serving `meta-llama/Llama-3.1-8B-Instruct` (FP16)
- `llama-8b-fp8-pool` — serving the same model in FP8
- One Inference Gateway routing `model=llama-8b` and `model=llama-8b-fp8` to the right pool

## Demonstration scripts

### 1. Multi-model routing

```bash
python3 scripts/send_mixed_traffic.py --multi-model
```

Sends 100 requests alternating between the two models. The script prints per-backend request counts pulled from the gateway's Prometheus metrics — you should see 50/50, and each request lands on the correct pool.

### 2. A/B traffic split

```bash
# Redeploy with the A/B split config (80% v1, 20% v2)
bash scripts/deploy_gateway.sh helm-values/values-ab-split.yaml

# Drive load
python3 scripts/send_mixed_traffic.py --ab-split

# Shift to 50/50 at runtime (no redeploy)
bash scripts/shift_traffic.sh 50 50

# Shift to 100% v2 — rollout complete
bash scripts/shift_traffic.sh 0 100
```

This is the canary deploy pattern: start small on v2, watch for regressions in your Grafana dashboard (see `projects/track6-perf-lab/`), then ramp. If v2 regresses, `shift_traffic.sh 100 0` rolls it back in seconds.

### 3. Independent autoscaling

```bash
kubectl apply -f helm-values/values-model-pool-hpa.yaml
kubectl get hpa -n llm-d -w
```

Each pool scales independently based on its own `vllm:num_requests_waiting` metric. Drive heavy load only to one model and watch the other stay flat.

## Deep Tech extensions

Pick one of these to push beyond the Builder lane:

- **Sticky routing by session ID** for prefix-cache reuse — hash `session_id` header to a specific replica. Measure cache hit rate climbing.
- **Shadow traffic** — send every request to both v1 and v2, return v1 to the user, log v2's output for offline comparison. Great way to A/B without risk.
- **Extend the llm-d benchmark harness** with multi-model scenarios — the event explicitly calls out "extend llm-d's benchmark harness" for this track. Direct path to the **Best Upstream Contribution** prize.

## Submission angles

- **"One gateway, two models, zero downtime rollouts"** — demo the traffic-shift flow live. Clear value prop.
- **"Canary-safe LLM deployments for vLLM shops"** — frame it as production-ready. Appeals to the Most Promising Startup prize.
- **Upstream PR** — contribute a `values-multi-model-example.yaml` to the llm-d repo, or add an autoscaling example to the inference scheduler's docs. Direct candidate for **Best Upstream Contribution**.

## Links

- [llm-d core repo](https://github.com/llm-d/llm-d)
- [llm-d inference scheduler](https://github.com/llm-d/llm-d-inference-scheduler)
- [llm-d Helm charts](https://github.com/llm-d/llm-d/tree/main/charts)
- [Gateway API — weighted routing](https://gateway-api.sigs.k8s.io/api-types/httproute/)
- [Kubernetes HPA with custom metrics](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/)
