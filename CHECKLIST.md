# Pre-Hackathon Checklist — vLLM Hackathon, April 25 2026

**Status as of 2026-04-24:** ~10 hours to event start (9:30 AM Sat).

## Tonight (must-do)

### Accounts
- [ ] **NVIDIA Brev account** — sign up at <https://brev.nvidia.com>. If you're a captain, create a team org and share the invite link so coupons pool (5× compute).
- [ ] **Hugging Face account + access token** — generate at <https://huggingface.co/settings/tokens>. Accept gated licenses NOW for:
  - `nvidia/NVIDIA-Nemotron-Nano-3-30B-A3B-BF16`
  - any Llama variants you might fall back to
- [ ] **Discord** — joined `red.ht/toa-discord` (announcements, support, team-finding)
- [ ] **Luma registration** — confirmed (registration closes when capacity hits)

### Local setup
- [x] Python 3.13 venv created at `agentbench-live/.venv`
- [x] Backend deps installed (openai, fastapi, uvicorn, websockets, pydantic, etc.)
- [x] Dashboard scaffolded (Vite + React) — run `npm install` in `dashboard/`
- [x] All four sub-systems built: subject_agent, benchmark_runner, optimizer_agent, nat_middleware
- [x] FastAPI server with WebSocket trace streaming
- [x] React dashboard with live Gantt + before/after metrics + optimizer recs

### Verify it boots
```powershell
cd "D:\Redhat Hackathon\agentbench-live"
.venv\Scripts\Activate.ps1
pytest -q                               # should pass
python -m uvicorn api_server.main:app   # should start :8000
# in another shell:
cd dashboard
npm run dev                              # should start :5173
```

## Hackathon-day morning (before 9:30 AM)

- [ ] Phone has Discord + Luma installed
- [ ] HF token + Brev creds in a password manager (NOT in `.env` committed to anywhere)
- [ ] Laptop charged + charger packed
- [ ] Route to **300 A Street, Boston** mapped (Seaport district)
- [ ] **Pitch ready** — 1 sentence: "Real-time vLLM agent profiler showing before/after optimization metrics on a live Gantt chart. Need [backend/frontend/ML] help."
- [ ] Headphones (open offices are loud)

## On arrival (9:30 AM doors)

1. Sign in, grab coffee, find the Discord channel
2. Find a team or pitch your project at the **10:45 AM team formation**
3. Captains: set up Brev team org, share invite, pool coupons
4. Boot the GPU box: `bash vllm_setup/00_install.sh` then `01_smoke_test.sh`
5. Pick the right serve script (Qwen3-8B if single 16 GB GPU, Nemotron if 40 GB+)

## MVP gate (Hour 10 — must hit)

Subject Agent runs end-to-end on vLLM. Same task with `--enable-prefix-caching`
ON vs OFF prints two timings to terminal showing measurable delta. **If you
hit this, everything else is polish.**

## Stretch goals (Hours 10-24)

- [ ] React Gantt chart streaming live spans
- [ ] Optimizer Agent recs panel populated automatically
- [ ] Speculative decoding wired up + measured impact
- [ ] Concurrent load test (10 parallel agents) showing nvext header impact
- [ ] Demo video as backup if live demo flakes
- [ ] 3-5 presentation slides

## Headline numbers to chase (judges will ask)

| Metric | Baseline | Optimized | Target |
|--------|----------|-----------|--------|
| End-to-end latency | ~8 s | ~3 s | **2-3× faster** |
| Avg TTFT | ~900 ms | ~120 ms | **5-8× faster** |
| Decode throughput | ~45 tok/s | ~70 tok/s | **1.5×+** |
| GPU utilization | ~40% | ~75% | **~2×** |
| Prefix cache hit | 0% | 85%+ | demonstrate |
