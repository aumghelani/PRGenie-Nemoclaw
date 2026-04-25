# ZeroClaw Code Assistant Demo

A hands-on demo showing how **quantized local LLMs** handle everyday coding tasks on your laptop, while **cloud models** handle complex reasoning — all orchestrated by [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw).

## Why this matters

| | Local (quantized LLM) | Cloud (Claude/GPT) |
|---|---|---|
| **Cost** | Free | ~$0.003/query |
| **Latency** | 2-5s (no network) | 5-15s (API round trip) |
| **Privacy** | Code stays on your machine | Sent to external API |
| **Quality** | Great for routine tasks | Better for deep reasoning |

The point: **80% of coding tasks don't need a cloud model.** A 4-bit quantized Llama 3.1 8B (~4.5 GB) running on your laptop handles code explanation, refactoring, and basic review just fine. Reserve cloud for architecture reviews, security audits, and complex debugging.

## Quick start (laptop)

```bash
# 1. Run the installer (installs Ollama + ZeroClaw, pulls quantized model)
bash install.sh

# 2. Set your cloud API key (only needed for cloud-routed tasks)
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Start ZeroClaw
zeroclaw start

# 4. Try it
# Local task (runs on your laptop):
#   "explain this code: def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)"
#
# Cloud task (routes to Claude automatically):
#   "do a security audit of the authenticate function in sample_code.py"
```

## Quick start (Brev GPU instance)

```bash
# 1. Start vLLM (pre-installed on Brev)
bash /workspace/start_vllm_server.sh

# 2. Install ZeroClaw
curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/main/scripts/bootstrap.sh | bash

# 3. Use the vLLM config
cp config.vllm.toml ~/.zeroclaw/config.toml
cp skills/*.md ~/.zeroclaw/workspace/skills/

# 4. Start
export ANTHROPIC_API_KEY="sk-ant-..."
zeroclaw start
```

## What's included

```
config.ollama.toml       # ZeroClaw config for laptop (Ollama backend)
config.vllm.toml         # ZeroClaw config for GPU instance (vLLM backend)
install.sh               # One-command setup for laptop
skills/
  code-explain.md        # Explain code (local)
  code-refactor.md       # Refactor code (local)
  code-review.md         # Quick code review (local)
  architecture-review.md # Deep architecture review (cloud)
  security-audit.md      # Security audit (cloud)
examples/
  sample_code.py         # Python file with intentional issues for testing
  walkthrough.md         # Step-by-step demo script
```

## How routing works

ZeroClaw uses **hint-based routing** to decide which model handles each request:

- **Skills** declare a `model_hint` (`local` or `reasoning`) in their frontmatter
- **Query classification** rules in `config.toml` auto-detect complex queries by keyword (e.g., "architecture", "security", "vulnerability") and route them to the cloud
- **Fallback** ensures that if the local model is down, queries still get answered via cloud

```
User query
    |
    v
[Query Classification] -- matches "security", "architecture" --> Cloud (Claude)
    |
    | (no match)
    v
[Local Model] -- Ollama or vLLM --> Response
```

## Requirements

**Laptop mode:**
- macOS or Linux
- 8 GB+ RAM (16 GB recommended)
- ~5 GB disk for the quantized model

**GPU mode:**
- Any Brev instance from the hackathon (Tier 1/2/3)
- vLLM already running with Llama 3.1 8B

## Full walkthrough

See [examples/walkthrough.md](examples/walkthrough.md) for a guided demo script you can follow during the hackathon.
