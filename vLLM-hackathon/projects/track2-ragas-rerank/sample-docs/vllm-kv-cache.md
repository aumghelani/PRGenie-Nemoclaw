# vLLM KV-Cache and PagedAttention

vLLM's flagship optimization is **PagedAttention**, which manages the KV-cache
using fixed-size pages (similar to virtual memory in an OS). Each request's
KV-cache is allocated page-by-page on demand rather than reserving a worst-case
contiguous buffer.

## Why this matters

Traditional LLM servers pre-allocate contiguous KV-cache buffers per request.
On long-context workloads this causes severe fragmentation — a request needing
4 KB might be denied because memory is split across small free regions.
PagedAttention's paged layout eliminates external fragmentation and enables
much higher concurrency at the same VRAM budget.

## Prefix caching

When two requests share an identical prefix (e.g., a common system prompt),
PagedAttention can share the same physical pages. vLLM exposes this via
`--enable-prefix-caching`. The metrics `vllm:gpu_prefix_cache_hit_tokens_total`
and `vllm:gpu_prefix_cache_query_tokens_total` let you track the hit rate.

## Implications for RAG

RAG workloads often repeat the same system prompt + retrieval format across
many queries. With prefix caching enabled and deterministic context ordering,
the prefix cache hit rate climbs steeply — reducing prefill cost for subsequent
queries. A prefix-cache-aware router (assigning similar queries to the same
vLLM replica) maximizes this benefit.
