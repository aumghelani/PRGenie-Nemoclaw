# Explain It Like I'm 10 — The Whole Hackathon Project

Hey. Don't panic. None of this is hard once you have the right pictures in
your head. This file walks you through **everything** from zero — what AI
is, what the tools are, what we built, and what each scary file does.

Read it top-to-bottom. It's long but each section is small.

---

## Part 1 — The Big Picture (1 paragraph)

Tomorrow you're at a hackathon where teams compete to build cool stuff
using **AI**. Specifically, you're using an AI tool called **vLLM** that
makes AI run faster. We built a project called **AgentBench Live** that
shows judges *how* and *why* it runs faster — like a fitness tracker for
AI. We measure the AI before tweaks, after tweaks, and show the speedup
on a pretty chart. That's it. That's the whole project.

---

## Part 2 — What is AI / LLM / "the model"?

You've used ChatGPT. The thing answering you is called a **Large Language
Model**, or **LLM** for short. Think of it as a super-smart parrot that
read the entire internet.

```
   Your question  ─►  ┌──────────────┐  ─►  Its answer
                      │    LLM       │
                      │ (the parrot) │
                      └──────────────┘
```

The parrot's "brain" is a giant pile of numbers (called **weights**).
Tens of billions of them. It learned these numbers by reading text for
months on a supercomputer.

When you ask a question, the LLM:
1. Reads your words one at a time
2. Predicts the next word that *should* come
3. Says it
4. Goes back to step 1, now with one more word added

That's literally it. It's fancy autocomplete.

---

## Part 3 — What is a GPU and why do we need one?

LLMs do **a LOT of math**. Not hard math — just additions and
multiplications — but BILLIONS of them per word.

| | CPU (regular processor) | GPU (graphics card) |
|---|---|---|
| Like… | 1 genius doing math | 10,000 kids doing math |
| Best for | Complicated logic | Simple math, lots of it |
| LLMs need | ❌ | ✅ |

So we run LLMs on GPUs. The GPU does all the math; the CPU just
coordinates.

The hackathon will give you access to **NVIDIA GPUs** (the company that
makes most AI GPUs) through a service called **Brev**. Brev is like
Airbnb for GPU computers — you rent one for a few hours.

```
  Your laptop ──── internet ───►  Rented GPU computer (on Brev)
   (no GPU)                      (has a big NVIDIA GPU)
                                  └──► runs vLLM + Nemotron
```

---

## Part 4 — What is Hugging Face?

**Hugging Face** (HF) is a website. Two things live on it:

1. **Models** — the actual AI brains, free to download. People upload
   their trained models, you download them. Like the App Store for AI.
2. **A login system** — for two reasons:
   - Some models require you to "sign a waiver" first (the model's
     creator wants to know who's using it)
   - Rate limits — they need to know who you are so one person can't
     hammer the servers

Your **HF token** is your library card. It proves it's you. You paste it
once on your computer and now you can download any model you've been
approved for.

```
   Hugging Face website
   ┌─────────────────────────────────────┐
   │                                      │
   │   📦 Llama-3                         │
   │   📦 Qwen3-8B                        │
   │   📦 Nemotron-3-Nano-30B  🔒 gated  │  ← need to "sign waiver"
   │   📦 ... thousands more              │
   │                                      │
   └─────────────────────────────────────┘
                ▲
                │ huggingface-cli login (paste token once)
                │
        Your computer
```

For our project we're downloading **Nemotron-3-Nano-30B-A3B-BF16**.
That mouthful means:
- **Nemotron-3-Nano** = NVIDIA's model family + version + size
- **30B** = 30 billion weights total
- **A3B** = only 3 billion are *active* at a time (more on this in a sec)
- **BF16** = each weight stored as a 16-bit number (precision setting)

### What does "30B but only 3B active" mean?

Modern AI models use a trick called **Mixture of Experts (MoE)**. Imagine
a hospital with 30 specialists. When you walk in with a sore throat,
you only see the *throat doctor* — not all 30. The other 29 are still in
the building (you "loaded" all 30 into memory) but you only "talk to" 3.

```
        Your question
              │
              ▼
        ┌──────────┐
        │ Router   │  ← picks 3 of 30 experts to consult
        └─────┬────┘
              │
   ┌──────────┼──────────┐
   ▼          ▼          ▼
 Expert    Expert     Expert
   (other 27 are sitting idle for THIS question)
```

Why? It's faster. You get the smarts of a big model without the cost of
running it all every time.

---

## Part 5 — What is vLLM?

You can run an LLM with a basic Python library, but it's slow. **vLLM**
is the *speed-optimized* way to run an LLM.

Think of it like this:

| | Regular Python (e.g. Transformers) | vLLM |
|---|---|---|
| Like… | A regular fridge | A walk-in restaurant fridge |
| Speed | OK for one person | Built for 1000s |
| Tricks | Few | Many (we'll see them) |

vLLM is **the** thing this hackathon is about. The whole event exists
because vLLM is open-source and Red Hat / NVIDIA / IBM / MIT-IBM are all
contributing to it.

When we say "run vLLM" we mean: start a program on the GPU computer that
loads the model and waits for questions. It exposes a website-style
endpoint at `http://localhost:5000/v1/chat/completions`. Anyone can send
questions to that URL and get answers.

```
    Your laptop  ───POST request─►  GPU computer running vLLM
      (browser /                      ┌────────────────────┐
       Python script)                 │ vLLM (fast engine) │
                                      │   loaded with      │
                                      │   Nemotron model   │
                                      │   on the GPU       │
                                      └────────────────────┘
                  ◄────answer─────────
```

---

## Part 6 — What "optimizations" does vLLM offer?

This is the heart of the hackathon. vLLM has tricks that make AI faster.
Each trick has a flag (a switch you flip ON when you start vLLM).

### Trick #1 — Prefix Caching ("the sticky note trick")

When an AI agent runs, it asks the same long instructions over and over:
*"You are a helpful research agent. Tools you can use: search, calculator,
database… [3000 words]… Now please answer: <new question>."*

The first 3000 words are the same EVERY time. Without prefix caching,
the AI re-reads them from scratch every time.

```
WITHOUT prefix caching (slow):
  Call 1: [read 3000 instruction words] [read question A] [answer]
  Call 2: [re-read same 3000 words]     [read question B] [answer]
  Call 3: [re-read same 3000 words]     [read question C] [answer]
                ^ wasted!

WITH prefix caching (fast):
  Call 1: [read 3000 instruction words] [read question A] [answer]
  Call 2: [skip — already know!]        [read question B] [answer]
  Call 3: [skip — already know!]        [read question C] [answer]
                                        ^ saved 90% of the work
```

**Speedup: 3-10× faster on calls 2, 3, 4…**

### Trick #2 — FP8 KV Cache ("compress the memory")

While the AI generates an answer, it remembers everything it just said
(its "working memory"). That memory takes a lot of GPU RAM.

FP8 means: store each number with 8 bits instead of 16. Half the size,
basically same accuracy.

```
Before:  ████████████████████  (32GB of working memory)
After:   ██████████            (16GB — fits more conversations!)
```

**Speedup: doubles how long a conversation can be.**

### Trick #3 — Speculative Decoding ("tag-team writing")

The AI generates one word at a time, slowly. Speculative decoding
adds a *small fast helper model* that drafts a few words ahead, and
the big model just checks them.

```
WITHOUT spec decoding (1 word at a time):
  Big model: "The"... "cat"... "sat"... "on"... "the"... "mat"...
              ^ slow ^ slow  ^ slow  ^ slow  ^ slow  ^ slow

WITH spec decoding:
  Small model drafts: "The cat sat on the mat"
  Big model checks all at once:  ✅ ✅ ✅ ✅ ✅ ✅
   → outputs all 6 words in 1 step instead of 6
```

**Speedup: 1.5-1.7× faster.** Works best on predictable text (like JSON).

### Trick #4 — Async Parallel Tools ("don't block")

If the agent says *"first search Google, then look up our database"* but
those don't depend on each other, you can do them at the same time.

```
WITHOUT parallel: 🔍 search ────► 📁 db lookup ────►
                  (1.0s)          (0.5s) = 1.5s total

WITH parallel:    🔍 search ────►
                  📁 db lookup ─►   = 1.0s total (max of the two)
                  (running together)
```

**Speedup: cuts time roughly in half when independent.**

### Trick #5 — nvext Headers ("VIP scheduling")

When the GPU is busy with many requests, vLLM has to pick which to do
first. nvext headers let your code say *"this request is the VIP one,
bump it to the front of the line."*

```
GPU's queue without headers:    [req1][req2][req3][req4]   <- random order
GPU's queue WITH headers:       [VIP-req3][req1][req2][req4]
                                       ^ the user's first impression call
```

**Speedup: -62% to -89% latency under load** (numbers from the meetup).

---

## Part 7 — What is an "agent"?

ChatGPT in your browser only talks. An **agent** is an AI that can also
USE TOOLS — search the web, do math, call APIs, query databases.

```
Regular LLM:               Agent:
  ┌────┐                     ┌────┐  ─search────►  Google
  │LLM │  ─just text─►       │LLM │  ─calculate─► Calculator
  └────┘                     │    │  ─lookup────► Database
                             └────┘  ←─results──
```

The agent works in a loop:

```
User: "What's the GDP of France compared to Germany?"

Step 1 (LLM call): plan
  → "I need to search for France GDP, search for Germany GDP, then compare."

Step 2 (tools): fetch data
  → search("France GDP 2026")  →  $3.0T
  → search("Germany GDP 2026") →  $4.5T

Step 3 (LLM call): synthesize
  → "Germany is ~1.5x larger"

Step 4 (LLM call): final answer
  → "France's GDP is $3.0T; Germany's is $4.5T. Germany is ~50% larger."
```

The agent makes **4 LLM calls** in this example. That's why prefix
caching matters so much — the giant instruction block is repeated 4×.

---

## Part 8 — Our Project: AgentBench Live

We built a tool that:

1. **Runs an agent** (the 4-call thing above)
2. **Times every step** with millisecond precision
3. **Shows the timing as a Gantt chart** (a chart with bars for each step)
4. **Re-runs with optimizations ON**
5. **Shows the before/after side-by-side**

It's a fitness tracker for the agent. Or a microscope. Or a stopwatch
with a GUI. Pick your analogy.

```
┌───────────────────────────────────────────────────────────────┐
│                  AgentBench Live (browser)                     │
├───────────────────────────────────────────────────────────────┤
│  Pick a task: [Compare 3 country economies ▼]   [Run]         │
│                                                                │
│  BASELINE (no optimizations)                                   │
│    plan        ████                                            │
│    search      ████████                                        │
│    db query    ████ (started AFTER search — wasted time!)      │
│    synthesize  ███████████                                     │
│    final       ████████████████████  (8 seconds total)        │
│                                                                │
│  OPTIMIZED                                                     │
│    plan       ██                                               │
│    search     ████  (running parallel)                         │
│    db query   ███   (running parallel)                         │
│    synthesize ████                                             │
│    final      ███████  (3 seconds total)                       │
│                                                                │
│  ┌──────────────────────────────────────┐                     │
│  │ End-to-end:    8.2s → 3.4s  (2.4×)   │                     │
│  │ TTFT:          890ms → 120ms (7.4×)  │                     │
│  └──────────────────────────────────────┘                     │
│                                                                │
│  Recommendations:                                              │
│   ✅ Enable prefix caching  (saved 1.0s)                       │
│   ✅ Parallelize tool calls (saved 1.2s)                       │
│   ✅ Speculative decoding   (1.6× decode)                      │
└───────────────────────────────────────────────────────────────┘
```

That picture above is the entire pitch. Judges see it, they get it,
they award the prize.

---

## Part 9 — How the Pieces Fit Together

```
  Your Windows laptop                    Brev GPU computer
  (browser + dashboard)                  (Linux + NVIDIA GPU)
  ┌────────────────────────┐             ┌──────────────────────┐
  │                         │             │                      │
  │   React dashboard       │             │   vLLM server        │
  │     (Gantt chart UI)    │             │   (loaded with       │
  │            │            │             │    Nemotron model)   │
  │            │ HTTP+WebSocket           │                      │
  │            ▼            │             │      ▲               │
  │   FastAPI server   ─────┼─── HTTP ────┼──────┘               │
  │   (Python backend)      │  (questions)│                      │
  │            │            │             │                      │
  │   Subject Agent         │             │                      │
  │   (4-LLM-call loop)     │             │                      │
  │            │            │             │                      │
  │   Optimizer Agent       │             │                      │
  │   (analyzes traces)     │             │                      │
  │                         │             │                      │
  └────────────────────────┘             └──────────────────────┘

   ↑ everything in agentbench-live/        ↑ what the bash scripts
     runs on YOUR LAPTOP                     in vllm_setup/ start up
                                             on the GPU computer
```

---

## Part 10 — What are the .sh files?

`.sh` = **shell script** = a recipe card for a Linux computer. Just a
list of commands the computer should run, one after another.

When you "run" `99_baseline_only.sh` on Linux, you type:

```
bash 99_baseline_only.sh
```

…and Linux executes the commands inside.

You're looking at `99_baseline_only.sh` right now. Let me translate it
line by line:

```bash
#!/usr/bin/env bash
   ↑ "use the bash interpreter"

# Baseline mode for the demo: prefix caching + spec decoding OFF, FP8 OFF.
# Pair with 04_serve_optimized.sh to produce the before/after metrics.
   ↑ comments — just notes for humans, computer ignores them

set -euo pipefail
   ↑ "stop on first error" — safety setting

source "$HOME/vllm-env/bin/activate"
   ↑ "turn on the Python environment we set up earlier"

exec vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 \
   ↑ "start vLLM, load this model from Hugging Face"
   --dtype auto \
      ↑ "pick a number precision automatically"
   --trust-remote-code \
      ↑ "this model has custom code, allow it"
   --served-model-name nemotron \
      ↑ "when clients ask for 'nemotron', that's me"
   --host 0.0.0.0 --port 5000 \
      ↑ "listen on port 5000, accept any connection"
   --enable-auto-tool-choice \
      ↑ "let the model decide when to call tools"
   --tool-call-parser qwen3_coder \
      ↑ "parse tool calls in this format"
   --no-enable-prefix-caching \
      ↑ "TURN OFF the trick (this is the SLOW baseline)"
   --max-model-len 32768 \
      ↑ "max conversation length: 32K tokens"
   --gpu-memory-utilization 0.92
      ↑ "use up to 92% of GPU memory"
```

So this whole file says: **"Start the SLOW version of the AI server,
with the prefix caching trick deliberately turned OFF, so we can show
how much it sucks before we turn the trick ON."**

Compare to `04_serve_optimized.sh` which has:
- `--enable-prefix-caching` (ON)
- `--kv-cache-dtype fp8` (compression ON)
- `--speculative-model …` (tag-team helper ON)

That's the FAST one. The whole demo is: run the slow one, run the fast
one, show the difference on the dashboard.

---

## Part 11 — Your Hackathon-Day Plan (Super Simple Version)

### Tonight (10 minutes total)

1. Go to https://huggingface.co/settings/tokens — make a "Read" token,
   put it in your password manager
2. Go to these 4 pages, click "Agree and access repository" on each:
   - https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
   - https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8
   - https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16
   - https://huggingface.co/Qwen/Qwen3-8B (might not need agreeing, but click anyway)
3. Sleep

### Tomorrow morning (before 9:30 AM)

- Charge laptop, pack charger
- Phone has Discord + Luma apps
- HF token + Brev creds in your password manager (NOT in a file)
- Map: 300 A Street, Boston

### At the venue

1. **Sign in, get coffee, sit down**
2. **Find your team** — your friend the captain. Confirm you're on the
   Brev team org.
3. **Wait for the talks** to end and hacking to start (around 11 AM)
4. **Open a Brev terminal** in your browser. You'll see something like:
   ```
   user@brev-box:~$ █
   ```
   That's a Linux command line.
5. **Copy our scripts to the Brev box.** Easiest way: clone our project:
   ```
   git clone https://github.com/<your-github>/agentbench-live
   ```
   (or zip it locally and drag it into the Brev file panel)
6. **Run setup**:
   ```
   cd agentbench-live
   bash vllm_setup/00_install.sh
   ```
   It'll ask for your HF token — paste it (input is hidden, that's normal)
7. **Smoke test**:
   ```
   bash vllm_setup/01_smoke_test.sh
   ```
   If it prints "PASS — vLLM is alive" you're golden.
8. **Start the SLOW server** in a tmux session:
   ```
   tmux new -s vllm
   bash vllm_setup/99_baseline_only.sh
   ```
   Press `Ctrl+B` then `D` to "detach" (it keeps running in the background)
9. **On your laptop**, point our app at the Brev box:
   ```
   set VLLM_BASE_URL=http://<brev-public-ip>:5000/v1
   .\scripts\dev_up.ps1
   ```
10. **Open http://localhost:5173** in your browser. You see the dashboard.
    Click "Run baseline" → watch the Gantt chart fill in slowly.
11. **Switch to optimized**: SSH back to Brev, kill the slow server
    (`tmux a -t vllm` then `Ctrl+C`), run `bash vllm_setup/04_serve_optimized.sh`
12. **Click "Run optimized"** in the dashboard. Watch the chart be MUCH
    shorter. The before/after table fills in with numbers. **You're done.**

---

## Part 12 — Words That Will Come Up (cheat sheet)

| Word | What it means in plain English |
|---|---|
| **LLM** | The AI brain (large language model) |
| **Token** | A chunk of text — usually 1 word or part of a word |
| **TTFT** | Time To First Token — how fast the AI starts replying |
| **Throughput** | How fast it generates words once it's started |
| **GPU** | The graphics card; runs all the AI math |
| **CUDA** | NVIDIA's software for using their GPUs |
| **Inference** | Just means "running" the AI to answer questions (vs training it) |
| **Quantization** | Squishing the model to use less memory (FP8, INT4, etc.) |
| **Prefix** | The repeated start of every prompt (instructions + tools) |
| **KV cache** | The AI's working memory while generating |
| **Tool calling** | Letting the AI use external functions (search, math, etc.) |
| **Agent** | An LLM that uses tools in a loop |
| **Endpoint** | A URL you can send questions to |
| **OpenAI-compatible** | Speaks the same protocol as ChatGPT's API (so any client works) |
| **vLLM** | The fast AI server we're using |
| **Hugging Face / HF** | The website where AI models live |
| **Brev** | NVIDIA's "rent a GPU" service |
| **Nemotron** | NVIDIA's family of AI models |
| **NeMo Agent Toolkit / NAT** | NVIDIA's library for building agents |
| **NemoClaw** | A security sandbox for agents (runs them safely) |
| **bash / shell** | Linux command line + scripts |
| **tmux** | Lets you keep a program running after you close the window |

---

## Part 13 — If Something Goes Wrong (panic prevention)

**"vLLM won't start, says CUDA something something"**
→ The Brev box doesn't have a working GPU driver. Ask the team captain
to swap to a different Brev image. There's an `nvidia-smi` command you
can run; if it doesn't print a table of GPUs, the GPU isn't visible.

**"Out of memory" errors**
→ The model is too big for the GPU. Use the 4B variant instead:
edit `03_serve_nemotron.sh` and change `30B-A3B-BF16` to `4B-BF16`.

**"Hugging Face says access denied"**
→ Either you didn't accept the license (go back to Part 11 step 2), or
the token wasn't pasted correctly. Run `huggingface-cli whoami` — if
it prints your username, the token is fine.

**"The dashboard shows 'waiting for telemetry…' forever"**
→ The agent can't reach vLLM. Check that `VLLM_BASE_URL` is correct and
that you can hit `http://<brev-ip>:5000/v1/models` from your laptop's
browser. If not, port forwarding isn't set up — ask Brev's UI to expose
port 5000 publicly.

**"The whole thing is too complicated, I just want a working demo"**
→ Skip Nemotron entirely. Use Qwen3-8B (`02_serve_qwen8b.sh`). Smaller,
no license issues, fits any GPU. The demo still works — you'll just say
"running on Qwen3 instead of Nemotron" if a judge asks.

---

## Part 14 — Your Pitch in 30 Seconds (memorize this)

> "Every AI agent is bottlenecked by inference. We built AgentBench Live
> — a tool that profiles an agent in real-time, shows you exactly which
> step is slow on a live Gantt chart, then auto-applies vLLM
> optimizations and shows the before/after speedup. Watch — *click* —
> baseline run takes 8 seconds. *Click* — optimized run takes 3 seconds.
> 7× faster TTFT just from prefix caching. All running locally on a
> single GPU with Nemotron, no cloud APIs."

That's it. You don't need to know more than that to win.

You got this. 🚀
