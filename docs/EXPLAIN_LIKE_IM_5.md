# What Is This Project? (Explain Like I'm 5)

---

## The Big Picture

Imagine you have a really smart robot helper. You ask the robot a question, and it has to do 4 big thinking steps + 8 small tasks to answer you. This takes a long time.

**Our project watches the robot work, figures out WHY it's slow, and makes it faster — then shows you a before/after on a screen.**

---

## The 4 Pieces of Our Stack

Think of it like a restaurant kitchen:

```
YOU (the customer)
    ↓
NAT — the head waiter (takes your order, watches everything)
    ↓
NemoClaw — the kitchen safety manager (makes sure nothing bad happens)
    ↓
vLLM — the cooking engine (actually cooks the food on GPU hardware)
    ↓
Nemotron — the chef's brain (the actual AI model doing the thinking)
```

---

## 1. What is Nemotron?

**Nemotron is the brain. It's the AI model.**

NVIDIA made it. Full name: **Nemotron-Nano 30B**.

Imagine a really smart book with 30 billion facts in it — but instead of reading all 30 billion every time you ask a question, it only reads 3 billion (the most relevant ones). That's the Mamba-Transformer trick: **30B total, only 3B active at once.** Super efficient.

It's special because:
- It's really good at **tool calling** (telling the robot to "go search the web" or "do math")
- It's small enough to run on one GPU
- It understands how to reason step-by-step (like a detective)

**Where does it come from?** HuggingFace. You download it from `nvidia/NVIDIA-Nemotron-Nano-3-30B-A3B-BF16` and serve it with vLLM.

---

## 2. What is vLLM?

**vLLM is the cooking engine. It runs Nemotron on the GPU.**

Without vLLM, running a big AI model is like cooking one meal at a time, throwing away all your prep work between meals, and starting fresh every time.

vLLM fixes that with 5 tricks:

| Trick | Simple Explanation | Speed Gain |
|---|---|---|
| **Prefix Caching** | Remember your prep work between meals (don't re-chop the onions) | 3-10x faster |
| **Speculative Decoding** | Guess the next 5 words, verify all at once instead of one by one | 1.5-1.7x faster |
| **FP8 KV Cache** | Write notes in shorthand instead of full sentences (uses less memory) | 2x more capacity |
| **Async Scheduling** | Overlap the chopping with the cooking (don't wait, just go) | 56% more throughput |
| **Continuous Batching** | Let new orders jump into the kitchen mid-cook | Better GPU use |

**In our project:** Our robot (the Subject Agent) makes 4 LLM calls per task, and each one starts with the same system prompt. Prefix Caching means calls 2, 3, 4 skip re-reading that prompt — **saving ~340ms per call.**

---

## 3. What is NemoClaw?

**NemoClaw is the kitchen safety manager and privacy bouncer.**

Full name: NVIDIA NemoClaw.

It wraps your whole agent in a **sandbox** — a safe room where:
- The agent can only talk to who it's allowed to talk to (network isolation)
- It can only read/write files it's allowed to touch (file access control)
- Private data doesn't leak out (data privacy)
- Security rules are written in a simple YAML config file

Think of it like a bouncer at a club with a list. Your agent can do stuff, but NemoClaw checks the list first.

**The privacy router part:** NemoClaw decides — should this request go to the **local Nemotron model** (private, fast) or to a **cloud endpoint** (more powerful, but data leaves your machine)? It routes automatically based on sensitivity.

**Why it matters for demos:** It proves to the judges that our agent runs within defined trust boundaries — it's not just a chatbot, it's a production-safe agentic system.

**How to install:**
```bash
curl -fsSL https://raw.githubusercontent.com/NVIDIA/NemoClaw/main/install.sh | bash
nemoclaw my-agent onboard
```

---

## 4. What is NeMo Agent Toolkit (NAT)?

**NAT is the head waiter — it watches and manages everything between your code and the AI.**

It sits in the middle and does 3 things:

**A) Tracing & Telemetry**
Every time the agent calls the AI or uses a tool, NAT records it:
- How long did it take? (milliseconds)
- How many tokens were generated?
- When did the first token appear? (TTFT = Time To First Token)
- What tool was called?

This is how AgentBench Live gets its live data — NAT is the spy in the kitchen taking notes.

**B) Agentic Headers (nvext)**
NAT adds secret labels to every LLM request, like sticky notes:
- "This request will probably be 200 tokens long" (OSL = Output Sequence Length)
- "This is the FIRST call in the chain — it's high priority"
- "This is a low-urgency background call"

vLLM reads these sticky notes and schedules requests smarter.

**C) OSL Prediction (the crystal ball)**
NAT watches 20% of your agent's runs, builds a model of how long responses tend to be, and predicts future lengths with ~90% accuracy. The inference server **knows how long the answer will be before it starts writing it.** That lets it pre-allocate memory and avoid stalls.

---

## How They All Connect — The Full Flow

```
User types: "Research climate change solutions"
        ↓
Subject Agent (our Python code)
        ↓
NAT intercepts → records start time, adds nvext headers
        ↓
NemoClaw checks security policy → OK, allowed
        ↓
vLLM receives request → hits prefix cache (system prompt already cached!)
        ↓
Nemotron thinks → "I need to: search web, read papers, synthesize, answer"
        ↓
4 LLM calls + 8 tool calls happen
        ↓
NAT records everything → builds trace JSON
        ↓
Optimizer Agent reads trace → "Call 2 wasted 340ms re-computing prefix. Fix: enable caching."
        ↓
Dashboard shows Gantt chart + before/after metrics live
```

---

## Why Nemotron Specifically?

Because it was built by NVIDIA to be the best at **agentic tasks** (multi-step reasoning with tools). Other models exist (Qwen3, Llama) but Nemotron:

1. Has native tool calling built-in (no hacks needed)
2. Is FP8-quantized (half the memory, same quality)
3. Uses the Mamba architecture for long context efficiency
4. Is the "home team" model for this NVIDIA-sponsored hackathon track

---

## What We Actually Built

```
AgentBench Live
├── Subject Agent      ← the robot being profiled (4 LLM calls, 8 tools)
├── Optimizer Agent    ← the second robot that analyzes the first one
├── FastAPI backend    ← connects everything
├── WebSocket stream   ← sends live data to the browser
└── React dashboard   ← shows Gantt chart + metrics + recommendations
```

The MVP is just: **run the agent twice (prefix caching OFF vs ON), print the two timings, show the speedup.** Everything else is the fancy dashboard on top.

---

## One-Sentence Summary

**Nemotron is the brain, vLLM is the engine that runs the brain fast, NemoClaw keeps the brain safe, and NAT watches the brain work — and our project measures exactly how fast the brain is, finds the slow parts, and fixes them automatically.**
