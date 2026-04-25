# Hackathon Use Cases

Real-world use cases for each project. These are designed to be **meaningful,
demo-worthy, and achievable within hackathon time constraints**. Pick one that
excites your team and build something the judges will remember.

---

## 1. Ask My Docs (Beginner RAG)

### Use Case A: Compliance Policy Assistant for Regulated Industries

**The Problem:** Financial services, healthcare, and legal teams maintain
hundreds of pages of compliance policies (SOC 2, HIPAA, GDPR, internal
guidelines). Employees regularly misinterpret rules or waste hours searching
for the right clause, leading to costly violations.

**What You Build:** A compliance Q&A assistant that ingests policy documents
and answers natural-language questions like *"Can we store EU customer data in
our US-East region?"* or *"What's our data retention policy for medical
records?"* with precise, cited answers grounded in actual policy text.

**Why It Wins:**
- Solves a real pain point with measurable cost (compliance violations cost
  companies millions)
- Demonstrates RAG's core value: grounding LLM answers in authoritative sources
- Easy to demo with sample compliance docs (GDPR excerpts, SOC 2 controls)
- Extend with source citation, confidence scores, and multi-document collections

**Suggested Extensions:**
- Add a "confidence meter" that flags when retrieved context is weak
- Support follow-up questions with conversation memory
- Color-code citations linking answers back to specific document sections
- Add an "audit trail" that logs every question and the sources used

---

### Use Case B: Engineering Onboarding Copilot

**The Problem:** New engineers at fast-moving startups face a wall of internal
docs, architecture decision records (ADRs), runbooks, and Slack-exported
knowledge. Ramping up takes weeks, and senior engineers spend hours answering
repeated questions.

**What You Build:** An internal knowledge copilot that ingests engineering
docs (architecture diagrams descriptions, runbooks, API docs, post-mortems)
and answers questions like *"How does our payment service handle retries?"* or
*"What's the deployment process for the mobile app?"*

**Why It Wins:**
- Directly reduces onboarding time (measurable business impact)
- Naturally showcases multi-format document ingestion (Markdown, text, PDFs)
- Demonstrates how companies like Notion, Confluent, and Stripe build internal
  AI tools
- Great demo: show a new hire asking progressively deeper questions

**Suggested Extensions:**
- Add PDF ingestion for architecture diagrams and design docs
- Create topic-specific collections (infra, backend, frontend, security)
- Implement "I don't know" detection when no relevant docs exist
- Add a feedback button so users can flag bad answers for improvement

---

## 2. Shrink to Fit (Beginner Quantization)

### Use Case A: Edge Deployment Cost Calculator for IoT/Mobile

**The Problem:** Companies deploying AI on edge devices (drones, medical
devices, retail kiosks, mobile apps) need to know: *"Can this model run on
our hardware, and what quality do we lose?"* Today, engineers spend days
manually testing different quantization levels on target hardware.

**What You Build:** A quantization trade-off dashboard that benchmarks
full-precision vs. quantized models and presents a clear cost/quality/speed
comparison. Include a "deployment recommendation engine" that, given a VRAM
budget (e.g., 6 GB for a Jetson Nano), recommends the best quantization
level.

**Why It Wins:**
- Answers a real engineering decision that every edge-AI company faces
- Produces concrete, data-driven output judges can evaluate
- The recommendation engine adds intelligence beyond simple benchmarking
- Easy to extend with cost calculations ($/token at different precision levels)

**Suggested Extensions:**
- Add cost-per-token estimates based on cloud GPU pricing (A10G, T4, L4)
- Include a "quality-critical threshold" slider for different domains
- Show real-time VRAM waterfall charts during inference
- Compare batch inference throughput (how many concurrent users can be served)

---

### Use Case B: Model Serving Budget Optimizer for Startups

**The Problem:** Startups burning through GPU cloud credits need to serve the
best model possible within a fixed monthly budget. A 4x reduction in VRAM
means 4x more users on the same hardware, or dropping from an A100 to a T4
(10x cost savings), but only if quality holds.

**What You Build:** A side-by-side quality and cost comparison tool that
quantifies exactly what you gain and lose with quantization. Include a
"monthly cost projection" that estimates cloud spend for a target QPS
(queries per second) at each precision level.

**Why It Wins:**
- Directly tied to business outcomes (saving money is universal)
- Produces a compelling visual: Pareto chart of cost vs. quality
- Demonstrates production thinking, not just academic benchmarking
- Judges can immediately understand the value proposition

**Suggested Extensions:**
- Add a "break-even calculator" showing when quantization ROI pays off
- Include quality comparison on domain-specific prompts (code, medical, legal)
- Model different traffic patterns (bursty vs. steady-state)
- Generate a one-page PDF report summarizing recommendations

---

## 3. Reward Ranker (Beginner RL)

### Use Case A: Customer Support Tone Calibrator

**The Problem:** Customer support AI often sounds either too robotic or too
casual. Different companies need different tones: a bank needs formal and
precise, a gaming company needs friendly and casual. Current models lack
fine-grained tone control, and prompt engineering is brittle.

**What You Build:** A preference collection and reward model training pipeline
focused on **tone alignment**. Collect preferences by judging response pairs
specifically on tone (empathetic vs. clinical, formal vs. casual), train a
reward model that captures your tone preference, then use it to automatically
score and rank new responses by tone appropriateness.

**Why It Wins:**
- Tone/style alignment is a real problem every company deploying chat AI faces
- The reward model produces a tangible artifact (a tone classifier)
- Easy to demo: show the model scoring responses and correctly ranking them
- Directly feeds into the Align It project for teams wanting to continue

**Suggested Extensions:**
- Create multiple reward models for different personas (formal, friendly, technical)
- Add a "tone spectrum" visualization showing where each response falls
- Include negative examples (passive-aggressive, dismissive) to sharpen the model
- Build a leaderboard ranking models by tone consistency

---

### Use Case B: Code Review Quality Scorer

**The Problem:** Code review quality varies wildly. Some reviews are
superficial ("LGTM"), while others catch subtle bugs and suggest elegant
improvements. Engineering orgs want to encourage high-quality reviews but
have no way to measure or incentivize them systematically.

**What You Build:** A preference pipeline where you judge pairs of code review
comments on the same code snippet. Train a reward model that learns what
constitutes a helpful code review (catches bugs, explains reasoning, suggests
improvements) vs. a low-effort one. Use it to score real review comments.

**Why It Wins:**
- Unique and creative application of RLHF beyond typical chat alignment
- Directly applicable to engineering productivity (every company does code reviews)
- The trained model produces measurable, verifiable scores
- Compelling demo: feed in real GitHub review comments, show quality rankings

**Suggested Extensions:**
- Categorize review quality dimensions (correctness, thoroughness, actionability)
- Integrate with sample GitHub PR data
- Build a "review coach" that suggests how to improve a low-scoring review
- Compare reward model scores against actual review outcomes (did the bug get caught?)

---

## 4. Speed Demon (Intermediate Speculative Decoding)

### Use Case A: Real-Time Coding Assistant Latency Optimizer

**The Problem:** AI coding assistants (like Copilot, Cursor) must respond in
under 500ms to feel "instant" during inline completions, but larger models
(70B) produce significantly better code suggestions. Speculative decoding
could let you serve a 70B model at near-8B latency, giving users premium
quality at interactive speeds.

**What You Build:** A benchmark suite that simulates a coding assistant
workload: short completions (function bodies, variable names), medium
completions (full functions), and long completions (class implementations).
Measure whether speculative decoding can bring 70B latency below the 500ms
threshold for short completions. Produce charts showing the "usability
boundary" where response time becomes imperceptible.

**Why It Wins:**
- Directly applicable to the hottest product category in AI (coding assistants)
- Defines a clear success metric (< 500ms latency for short completions)
- Produces actionable, publication-quality charts
- Demonstrates understanding of both ML optimization and product UX requirements

**Suggested Extensions:**
- Test with actual code completion prompts from popular languages
- Measure acceptance rates for different code patterns (boilerplate vs. novel logic)
- Add concurrent user simulation (what happens with 10 engineers using it simultaneously)
- Compare against a quantized 70B to see if speculation + quantization stack

---

### Use Case B: Conversational AI Throughput Scaling for Contact Centers

**The Problem:** Enterprise contact centers handle thousands of concurrent
customer conversations. Each conversation requires low-latency responses from
a high-quality model. The business question: *"How many concurrent
conversations can one 2xA100 node handle at acceptable latency?"* Speculative
decoding could dramatically increase that number.

**What You Build:** A load-testing framework that simulates concurrent
multi-turn conversations against a 70B model, with and without speculative
decoding. Measure how throughput scales as concurrency increases (1, 4, 8, 16,
32 simultaneous conversations). Find the "breaking point" where latency
exceeds the 2-second SLA threshold.

**Why It Wins:**
- Solves a real infrastructure capacity planning problem
- The "conversations per node" metric is immediately meaningful to business stakeholders
- Produces a clear capacity curve that any engineering manager can act on
- Combines performance engineering with product thinking

**Suggested Extensions:**
- Model different conversation patterns (quick FAQ vs. complex troubleshooting)
- Calculate cost-per-conversation at each concurrency level
- Add a "burst mode" test simulating traffic spikes
- Compare tensor parallelism configurations (2-way vs. 4-way)

---

## 5. Compress & Compare (Intermediate Quantization)

### Use Case A: Medical NLP Quantization Safety Audit

**The Problem:** Healthcare AI companies want to deploy quantized models for
cost reasons, but medical applications have zero tolerance for quality
degradation on safety-critical outputs. A model that confuses drug dosages
or misclassifies symptoms after quantization could cause patient harm. No
systematic methodology exists for auditing quantization safety in medical
contexts.

**What You Build:** A quantization safety audit pipeline that goes beyond
generic benchmarks. Quantize with GPTQ and AWQ, then evaluate on
medical-specific test cases: drug interaction questions, symptom
interpretation, dosage calculations, and clinical reasoning. Produce a
"quantization safety scorecard" showing exactly where each method degrades
and whether the degradation is clinically significant.

**Why It Wins:**
- High-stakes, high-impact domain where getting it right truly matters
- Goes beyond generic benchmarks to domain-specific evaluation
- The "safety scorecard" is a novel, practical deliverable
- Demonstrates the kind of rigorous evaluation real healthcare AI companies need

**Suggested Extensions:**
- Add "failure mode analysis" categorizing types of errors (factual, numerical, reasoning)
- Include confidence calibration (does the quantized model know when it's uncertain?)
- Create a "safe deployment checklist" based on findings
- Test with different calibration datasets (general vs. medical-specific)

---

### Use Case B: Multi-Language Model Compression for Global Deployment

**The Problem:** Companies serving global markets need models that work well
across languages. Quantization can disproportionately degrade performance on
lower-resource languages (Hindi, Arabic, Swahili) while barely affecting
English. Without measuring this, companies unknowingly ship worse experiences
to non-English users.

**What You Build:** A cross-lingual quantization evaluation pipeline. Quantize
Llama 3.1 8B with GPTQ and AWQ, then benchmark quality across multiple
languages using translation tasks, multilingual QA, and language-specific
reasoning. Produce a "language equity dashboard" showing quantization impact
per language, highlighting which languages are most affected.

**Why It Wins:**
- Addresses a real fairness/equity concern in AI deployment
- Novel angle on quantization that hasn't been widely explored
- Produces a visually compelling dashboard with clear per-language comparisons
- Demonstrates awareness of responsible AI practices

**Suggested Extensions:**
- Test with language-specific calibration data to see if it reduces disparities
- Include script-specific analysis (Latin vs. CJK vs. Arabic scripts)
- Add recommendations for which quantization method is safest per language
- Create a Pareto chart with language equity as an axis alongside speed and quality

---

## 6. Align It (Intermediate DPO)

### Use Case A: Safety-Focused Model Alignment for Enterprise Deployment

**The Problem:** Base LLMs can generate harmful, biased, or inappropriate
content. Before deploying internally, enterprises need to align models to
refuse dangerous requests, avoid generating PII, and stay within policy
boundaries. Off-the-shelf alignment may not match a company's specific
safety requirements (e.g., a children's education platform has stricter needs
than a developer tool).

**What You Build:** A custom safety alignment pipeline using DPO. Generate
preference pairs focused on safety scenarios: harmful requests (chosen =
polite refusal, rejected = compliance), PII handling (chosen = redaction,
rejected = exposure), and bias (chosen = balanced, rejected = stereotyping).
Train a LoRA adapter, serve it, and demonstrate measurable improvement in
safety behavior with before/after evaluation.

**Why It Wins:**
- Safety alignment is the #1 concern for enterprise LLM adoption
- Produces a measurable improvement with clear before/after metrics
- The LoRA adapter is a tangible, deployable artifact (~100 MB)
- Demonstrates the exact workflow companies like Anthropic use internally

**Suggested Extensions:**
- Create a "red team" evaluation with adversarial prompts
- Sweep beta values and show the safety-helpfulness trade-off curve
- Test robustness against jailbreak attempts before and after alignment
- Combine with Reward Ranker to use custom reward model for evaluation

---

### Use Case B: Technical Writing Style Transfer for Documentation Teams

**The Problem:** Large organizations produce inconsistent technical
documentation. Different teams write in different styles: some are verbose,
others terse; some use jargon, others don't. Companies want a model that
generates documentation in a consistent, house style (clear, concise,
example-rich, jargon-free) regardless of the topic.

**What You Build:** A style alignment pipeline using DPO. Generate preference
pairs where the "chosen" response follows your defined style guide (concise,
uses examples, avoids jargon, includes code snippets where relevant) and the
"rejected" response is verbose, jargon-heavy, or lacks examples. Train a
LoRA adapter and demonstrate that the aligned model consistently produces
documentation in the target style.

**Why It Wins:**
- Practical, immediately useful application of DPO beyond safety
- Style consistency is a real problem for companies producing documentation
- Easy to demo: show side-by-side outputs on the same technical topic
- The style guide criteria make evaluation objective and measurable

**Suggested Extensions:**
- Define multiple style profiles (API reference vs. tutorial vs. quickstart)
- Measure style consistency across diverse technical topics
- Add readability scoring (Flesch-Kincaid) as an automated metric
- Build a "style compliance checker" using the aligned model as a judge

---

## 7. Infinite Scale (Advanced Distributed Inference)

### Use Case A: Traffic-Spike Resilient Inference for E-Commerce Events

**The Problem:** E-commerce platforms using AI for product recommendations,
search, and customer chat see 10-50x traffic spikes during events like Black
Friday, Prime Day, or flash sales. Traditional monolithic LLM serving either
over-provisions (expensive) or collapses under load (lost revenue).
Disaggregated serving with intelligent autoscaling can handle spikes gracefully.

**What You Build:** A disaggregated inference cluster that demonstrates
resilient scaling under simulated e-commerce traffic patterns. Implement a
load test that mimics realistic patterns: steady baseline, gradual ramp to
peak (10x), sudden burst (flash sale), and cool-down. Configure autoscaling
policies that keep latency under SLA during spikes while scaling down during
quiet periods. Produce a dashboard showing pod scaling, latency, and GPU
utilization throughout the event.

**Why It Wins:**
- Directly applicable to a high-value business scenario (e-commerce AI)
- Demonstrates the real advantage of disaggregated serving (independent scaling)
- The traffic pattern simulation makes the demo compelling and realistic
- Produces infrastructure-grade observability (Prometheus metrics, dashboards)

**Suggested Extensions:**
- Add cost tracking showing $/request at different scale points
- Implement priority routing (premium customers get dedicated decode capacity)
- Test graceful degradation (what happens when autoscaling can't keep up)
- Add a "capacity report" estimating infrastructure needs for target traffic

---

### Use Case B: Multi-Tenant LLM Platform with Workload Isolation

**The Problem:** AI platform teams serving multiple internal teams (search,
recommendations, chat, analytics) need workload isolation so one team's
traffic spike doesn't degrade another's latency. Disaggregated serving
enables this by routing different workload types to different pools with
independent scaling policies.

**What You Build:** A multi-tenant inference platform where different workload
types are routed to appropriate pools. Short prompts (search queries,
classifications) go to a combined fast-path, while long prompts (document
summarization, code generation) are split across prefill and decode pools.
Configure per-workload autoscaling and demonstrate that a traffic spike in one
workload type doesn't affect another's latency.

**Why It Wins:**
- Solves a real platform engineering challenge at scale
- Demonstrates sophisticated routing and resource isolation
- The "no cross-tenant interference" metric is compelling and verifiable
- Showcases production-grade infrastructure thinking

**Suggested Extensions:**
- Add tenant-level rate limiting and fair scheduling
- Implement SLA tiers (Gold, Silver, Bronze) with different latency targets
- Test failure isolation (kill one tenant's decode pod, verify others unaffected)
- Build a "capacity planner" that recommends pool sizes per tenant based on traffic

---

## How to Pick Your Use Case

| If you care about... | Start here |
|---|---|
| Building something you can demo in 5 minutes | Ask My Docs (A or B) |
| Saving real money on GPU costs | Shrink to Fit (B) or Compress & Compare (B) |
| AI safety and responsible deployment | Align It (A) or Compress & Compare (A) |
| Maximum "wow factor" for judges | Speed Demon (A) or Infinite Scale (A) |
| Solving a unique, creative problem | Reward Ranker (B) or Compress & Compare (B) |
| Production infrastructure experience | Infinite Scale (A or B) |

---

*Pick a use case, make it your own, and ship something real. Good luck!*
