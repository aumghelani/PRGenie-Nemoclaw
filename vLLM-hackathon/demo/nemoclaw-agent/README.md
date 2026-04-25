# Track 5 — NVIDIA GPU Prize: Agentic Edge powered by NemoClaw

Build the next generation of autonomous applications. This track focuses on using **[NemoClaw](https://github.com/NVIDIA/NemoClaw)** to create high-accuracy, steerable agents that leverage **vLLM**'s high-throughput inference.

Sponsored by **NVIDIA** — the winning team in this track takes home the NVIDIA GPU Prize.

## Why NemoClaw + vLLM

- **NemoClaw** is NVIDIA's open-source sandbox for autonomous agents: network isolation, filesystem policy, and routed inference all in one runtime.
- **vLLM** provides the high-throughput inference backend — the same engine the rest of the hackathon is built on.
- Together, you get fast inference with enforced safety boundaries, and the agent loop can route to local vLLM or NVIDIA cloud depending on the task.

## Three tiers

### Starter — Vibe-code an agent UI

Use `starter-template.py` as your scaffold. Open it in **Cursor** (or any AI coding tool connected to your Brev instance via SSH) and describe the product you want:

- "Build a customer support bot for a SaaS product"
- "Build a research assistant that reads arXiv papers"
- "Build an internal IT helpdesk with escalation to Slack"

The template has a working vLLM connection and a single retrieval tool. Let your AI coder build the UI, add domain data, and ship something demoable in a few hours.

### Builder — Multi-turn agentic workflow

Use `customer_support_agent.py` as the reference. It demonstrates:

- 4 tools (KB search, order lookup, ticket creation, human escalation)
- OpenAI-compatible function-calling wired into vLLM
- Multi-turn loop with tool result feedback
- Clean tool dispatch and error handling

Your challenge: extend it to a domain of your choice and demonstrate **superior reasoning and tool-calling vs. a stock base model**. Some ideas:

- Add more tools (email, calendar, CRM)
- Add conversation memory (SQLite or vector store)
- Add guardrails for dangerous tool calls (refund > $X, data deletion)
- Prove accuracy gains on a test set you define

### Deep Tech — Optimize the agent loop

Run `benchmarks/latency-test.py` with different inference profiles:

```bash
python3 benchmarks/latency-test.py --profile vllm           # baseline
python3 benchmarks/latency-test.py --profile vllm-steered   # with steering
python3 benchmarks/latency-test.py --profile nim-local      # NIM container
python3 benchmarks/latency-test.py --profile nvidia-cloud   # cloud Nemotron
```

Deliverables:

- Implement **custom steering** for NemoClaw (structured outputs, tool schema enforcement, max-tool-calls-per-turn)
- Benchmark and **quantify the latency/accuracy trade-offs** between profiles
- Optimize the agent loop — KV cache reuse, speculative decoding, disaggregated prefill (Track 3/4 techniques), anything that helps
- Present results: throughput, per-turn latency, tool-call success rate, cost per 1k conversations

## Quick start

```bash
# 1. Start your vLLM server (already running on Brev Tier 1/2/3 instances)
bash /workspace/start_vllm_server.sh

# 2. Install NemoClaw and onboard with the vLLM profile
bash setup.sh

# 3. Connect to the sandbox
nemoclaw agentic-edge connect

# 4. Run the Starter template (vibe-code from here)
python3 /workspace/starter-template.py

# 5. Or jump straight to the Builder reference
python3 /workspace/customer_support_agent.py

# 6. Benchmark (Deep Tech)
python3 /workspace/benchmarks/latency-test.py --profile vllm
```

## What's in this directory

```
README.md                    # This file
setup.sh                     # Installs NemoClaw + onboards with vLLM profile
blueprint.yaml               # NemoClaw inference profiles, tools, network policy
starter-template.py          # Starter-tier: minimal scaffold to vibe-code on
customer_support_agent.py    # Builder-tier: full multi-turn agent reference
tools/
  knowledge_base.py          #   Tool: KB search (mock corpus included)
  orders.py                  #   Tool: order lookup (mock data)
  tickets.py                 #   Tool: support ticket creation
  escalation.py              #   Tool: human handoff
benchmarks/
  latency-test.py            # Deep Tech: compare inference profiles
```

## Judging criteria

- **Starter:** demoable UI, clear use case, works end-to-end
- **Builder:** multi-turn correctness, tool-calling accuracy, quality of the custom domain
- **Deep Tech:** measurable latency/accuracy gains, rigorous benchmarks, novel steering techniques

## Links

- [NemoClaw (NVIDIA)](https://github.com/NVIDIA/NemoClaw)
- [NemoClaw (brevdev)](https://github.com/brevdev/NemoClaw)
- [NemoClaw Developer Guide — Local Inference](https://docs.nvidia.com/nemoclaw/latest/inference/use-local-inference.html)
- [NVIDIA Tech Blog — Build a Secure Local AI Agent](https://developer.nvidia.com/blog/build-a-secure-always-on-local-ai-agent-with-nvidia-nemoclaw-and-openclaw/)
- [NVIDIA Nemotron models](https://build.nvidia.com/explore/discover)
