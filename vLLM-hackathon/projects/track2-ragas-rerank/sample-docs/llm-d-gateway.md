# llm-d Inference Gateway

The llm-d **Inference Gateway** is the entry point for a Kubernetes-native LLM
serving cluster. It sits in front of a pool of vLLM replicas and handles
request routing, load balancing, and multi-model traffic.

## Responsibilities

- **Request routing**: direct requests to the vLLM replica serving the target
  model. For deployments with multiple models, maps `model` field in the
  request to the correct pool.
- **Load balancing**: default is round-robin across ready replicas. Supports
  sticky routing by session ID for prefix-cache reuse.
- **Disaggregated serving**: when prefill and decode run in separate pools,
  the gateway coordinates KV-cache handoff between them.
- **Metrics**: exports Prometheus metrics for end-to-end latency, per-model
  request rate, and prefill/decode pool utilization.

## A/B traffic split

For rolling out a new model version, configure weighted routing in the
gateway's values.yaml:

```yaml
gateway:
  routes:
    - match: { model: "llama-3.1-8b" }
      weights:
        - backend: llama-8b-v1-pool
          weight: 80
        - backend: llama-8b-v2-pool
          weight: 20
```

## Autoscaling

HPAs can scale decode and prefill pools independently based on per-pool
metrics. Typical targets: `vllm:num_requests_waiting` for decode; prefill
token throughput for the prefill pool.
