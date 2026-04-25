# Infinite Scale — Disaggregated Prefill/Decode with llm-d on Kubernetes

**Level:** Advanced | **Tier:** 3 (Deep Tech) | **GPU:** 4x A100 (80 GB)

Deploy a fully disaggregated inference system on Kubernetes where the prefill
and decode phases run on separate GPU pools. Use llm-d's KV-cache-aware routing
to efficiently transfer state between pools, and configure autoscaling based on
real-time Prometheus metrics.

---

## Quick Start

```bash
# 1. Deploy the full stack (kind cluster + llm-d + monitoring)
bash deploy.sh

# 2. Run a load test with ramping concurrency
python3 load_test.py

# 3. Watch the real-time scaling dashboard
python3 dashboard.py
```

---

## Architecture

```
                            +-----------+
            Requests -----> |  Gateway  | (KV-cache-aware router)
                            +-----+-----+
                                  |
                    +-------------+-------------+
                    |                           |
              +-----v------+            +------v-----+
              | Prefill Pool|            | Decode Pool |
              | (2x A100)   |            | (2x A100)   |
              +-----+------+            +------+-----+
                    |                           ^
                    |    KV-cache transfer       |
                    +---------------------------+

  Prefill:  Process full prompt, generate KV-cache (compute-bound)
  Decode:   Auto-regressive token generation (memory-bound)

  Separating them allows independent scaling and GPU specialization.
```

---

## Files

| File | Purpose |
|---|---|
| `deploy.sh` | Full deployment pipeline (cluster + llm-d + Prometheus) |
| `autoscale-policy.yaml` | HorizontalPodAutoscaler configs for prefill/decode |
| `prometheus-rules.yaml` | Custom metrics and alerting rules |
| `load_test.py` | Ramp concurrency and measure scaling behavior |
| `dashboard.py` | Real-time terminal dashboard (pods, metrics, GPU) |

---

## What to Measure

| Metric | Why it matters |
|---|---|
| **TTFT under load** | Does disaggregation keep prefill latency stable? |
| **Decode throughput** | Tokens/sec as decode pool saturates |
| **KV-cache transfer time** | Overhead of moving state between pools |
| **Autoscale reaction time** | How fast do new pods spin up? |
| **GPU utilization per pool** | Are prefill and decode GPUs used efficiently? |

---

## Ideas to Extend

- **Custom routing policy:** Route short prompts to a combined worker, long ones to disaggregated pools
- **Multi-model serving:** Serve 8B and 70B behind the same gateway
- **Preemption strategies:** Prioritize low-latency requests over batch workloads
- **Failure injection:** Kill a decode pod and observe recovery
- **Cost modeling:** Calculate $/token at different scaling points
