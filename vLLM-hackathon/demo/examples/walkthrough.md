# Demo Walkthrough: Local LLM Code Assistant with ZeroClaw

This walkthrough shows how a quantized local LLM handles everyday coding tasks, while complex reasoning routes to a cloud model automatically.

---

## Setup (2 minutes)

```bash
# From the demo/ directory
bash install.sh

# Set your cloud API key (needed only for cloud-routed tasks)
export ANTHROPIC_API_KEY="sk-ant-..."

# Start ZeroClaw
zeroclaw start
```

---

## Part 1: Local Tasks (runs on your laptop, no API key needed)

### 1.1 — Explain Code

Paste the `process_data` function from `sample_code.py` and ask:

```
explain this code:

def process_data(items):
    result = []
    for i in range(len(items)):
        item = items[i]
        if item is not None:
            if isinstance(item, str):
                item = item.strip()
                if len(item) > 0:
                    item = item.lower()
                    if item not in result:
                        result.append(item)
    ...
```

**What happens:** ZeroClaw routes this to the local Llama 3.1 8B model via Ollama. Response arrives in 2-5 seconds. No API call, no cost.

### 1.2 — Refactor Code

```
refactor this for readability:

def calculate_stats(numbers):
    if len(numbers) == 0:
        return None
    total = 0
    for n in numbers:
        total = total + n
    average = total / len(numbers)
    ...
```

**What happens:** Local model produces a clean version using `sum()`, `statistics.median()`, etc. Fast, free, private.

### 1.3 — Quick Code Review

```
review this code:

def authenticate(username, password):
    conn = sqlite3.connect("users.db")
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    ...
```

**What happens:** Local model catches the SQL injection and plaintext password issues. Good enough for a quick review.

---

## Part 2: Cloud Tasks (routes to Claude automatically)

### 2.1 — Architecture Review

```
review the architecture of this code — evaluate the overall design,
separation of concerns, and scalability of the APIHandler, Cache,
and authentication system in sample_code.py
```

**What happens:** The query matches the `architecture` keyword classification. ZeroClaw automatically routes to Claude Sonnet. You'll see a more thorough analysis covering design patterns, dependency management, and scalability trade-offs.

### 2.2 — Security Audit

```
do a security audit of the authenticate, create_user, and do_POST
handler functions — find all vulnerabilities and suggest fixes
```

**What happens:** Routes to Claude via the `security` keyword classification. The cloud model identifies SQL injection, command injection, MD5 hashing, and other OWASP issues with detailed remediation steps.

---

## Part 3: Compare (the "aha" moment)

Run the same security audit prompt twice — once forcing local, once forcing cloud:

```bash
# Force local model
zeroclaw agent --provider ollama -m "security audit: [paste authenticate function]"

# Force cloud model
zeroclaw agent --provider anthropic -m "security audit: [paste authenticate function]"
```

Compare:
- **Speed:** Local is faster (no network round trip)
- **Depth:** Cloud gives more thorough analysis with specific CVE references
- **Cost:** Local is free; cloud costs ~$0.003 per query
- **Privacy:** Local keeps your code on your machine

**The takeaway:** Use local for 80% of tasks (explain, refactor, quick review). Route to cloud for the 20% that need deep reasoning (architecture, security, complex debugging). Quantization makes the local model small enough to run on a laptop while keeping quality high enough for everyday coding tasks.

---

## Switching to vLLM (GPU instance)

On a Brev GPU instance, swap the config to use vLLM instead of Ollama:

```bash
# Start vLLM (already running on Brev instances)
bash /workspace/start_vllm_server.sh

# Switch ZeroClaw to vLLM backend
cp config.vllm.toml ~/.zeroclaw/config.toml

# Restart (or let hot-reload pick it up)
zeroclaw start
```

Same skills, same routing — but now the local model runs on GPU with much higher throughput. This is the production path: quantized models on GPU for team-wide inference, cloud fallback for complex tasks.
