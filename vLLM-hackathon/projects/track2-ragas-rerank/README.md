# Track 2 Builder — LlamaIndex + Reranker + RAGAs Evaluation

Reference project for the Track 2 **RAG on Open Inference** Builder lane. Covers the three things the official page calls out that are missing elsewhere in the repo:

> Build multimodal RAG with vision-language models. Evaluate retrieval quality with **RAGAs** metrics. Implement **reranking** and hybrid search.

This project focuses on the retrieval-quality side: **LlamaIndex** as the RAG framework, **BGE reranker** for two-stage retrieval, and **RAGAs** metrics to measure whether the retrieval is actually helping.

## What's here

```
README.md                    # This file
ingest.py                    # Chunk + embed documents into ChromaDB via LlamaIndex
query_with_reranker.py       # Two-stage retrieval: embed top-50 → rerank → top-5
eval_with_ragas.py           # Score answers with RAGAs (faithfulness, relevancy, precision)
app.py                       # Gradio UI wired to the pipeline
sample-docs/                 # Starter corpus (vLLM + llm-d documentation excerpts)
```

## Quick start

```bash
# 1. vLLM already running at :8000 (on your Brev instance)
# 2. Install track-specific deps
pip install llama-index llama-index-vector-stores-chroma llama-index-embeddings-huggingface \
    llama-index-postprocessor-flag-embedding-reranker ragas

# 3. Ingest docs
python3 ingest.py --docs sample-docs/ --persist ./chroma_db

# 4. Query with reranking
python3 query_with_reranker.py "How does vLLM handle KV-cache?"

# 5. Run RAGAs eval on a canned Q/A set
python3 eval_with_ragas.py
```

## Why LlamaIndex (vs. LangChain)?

Both are first-class on the event page. This project uses LlamaIndex because:

- Two-stage retrieval (embed → rerank) is a first-class concept via `NodePostprocessor`
- Easier to plug in multiple vector stores and compare
- Better tracing hooks for RAGAs instrumentation

The existing `projects/beginner-ask-my-docs/` covers LangChain — attendees can port between them to see the differences.

## The two-stage retrieval story

Naive RAG embeds the query, retrieves top-K by cosine similarity, and hands the top-K to the LLM. This is fine for simple corpora but breaks down when:

- Queries are ambiguous and the embedding model retrieves false positives
- Multiple chunks are near-duplicates and crowd out genuinely different hits
- The top result is "correct-ish" but a later result is actually the best match

**Two-stage retrieval** fixes this:

```
  Query
    ↓  (cheap) embed + cosine
  Top-50 candidates  
    ↓  (expensive) cross-encoder reranker scores each (query, candidate) pair
  Top-5 (reordered)
    ↓
  LLM
```

The reranker (`BAAI/bge-reranker-large`) is a cross-encoder that actually looks at both query and candidate together — much higher quality, ~10× slower per candidate. Running it only on the top-50 keeps latency reasonable.

## RAGAs — why it matters

The event page says Builder-lane teams must "evaluate retrieval quality with RAGAs metrics." The key metrics:

- **Faithfulness** — does the answer stay grounded in the retrieved context, or hallucinate?
- **Answer Relevancy** — is the answer actually relevant to the question?
- **Context Precision** — are the retrieved chunks useful for answering?
- **Context Recall** — did we retrieve everything we needed?

You need these numbers in your 2-min demo. "We built a RAG system" without metrics loses to "we built a RAG system with 87% faithfulness." The `eval_with_ragas.py` script produces these.

## Deep Tech extension: prefix-cache-aware routing

The official Deep Tech ask is **prefix-cache-aware query routing** to minimize KV-cache misses. Sketch of the approach:

1. Standardize your system prompt + retrieved context format
2. Use consistent chunk IDs so identical context reuses vLLM's prefix cache
3. Route similar queries to the same vLLM replica (hash-based sticky routing via llm-d Inference Gateway)

`query_with_reranker.py` already produces deterministic, ordered context which makes prefix reuse effective. Benchmark the hit rate with the Track 6 Grafana dashboard (`vllm:gpu_prefix_cache_hit_tokens_total`).

## Submission angles

- **"RAG with real numbers"** — a clean metrics page is rare; RAGAs output is compelling to judges
- **"Prefix-cache-aware RAG"** — compute `cache_hit_rate = hit_tokens / query_tokens` and show it trending up as you add sticky routing — direct Inference Efficiency Impact points
- **"Multimodal RAG"** — swap the chunker for a PDF processor with page images, use Llama 3.2 Vision as the LLM (Builder-lane bonus points)

## Links

- [LlamaIndex](https://docs.llamaindex.ai/)
- [RAGAs](https://docs.ragas.io/)
- [BGE Reranker (BAAI)](https://huggingface.co/BAAI/bge-reranker-large)
- [vLLM prefix caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html)
