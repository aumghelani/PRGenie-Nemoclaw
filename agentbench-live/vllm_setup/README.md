# vLLM Server Setup (Linux / Brev / WSL2)

These scripts run on the **GPU host** — NVIDIA Brev, hackathon-provided cloud, or WSL2 with a CUDA-passthrough GPU. They will NOT work on Windows directly.

## Order of Operations on Hackathon Day

1. SSH into the Brev box (or open Brev terminal in browser)
2. Run `00_install.sh` once to set up the environment + vLLM
3. Run `01_smoke_test.sh` to verify the install with a tiny model
4. Run **one** of the serve scripts in a tmux/screen session:
   - `02_serve_qwen8b.sh` — fallback (16 GB GPU, fast iteration)
   - `03_serve_nemotron.sh` — recommended (40 GB+ GPU)
   - `04_serve_optimized.sh` — same as nemotron but with FP8 KV + spec decoding ON
5. Verify the endpoint is up: `curl http://localhost:5000/v1/models`
6. Point the agent client at `http://<brev-ip>:5000/v1` (or use Brev's port forwarding)

## Optimization toggles (battle-plan section 5)

| Flag | When to use |
|------|-------------|
| `--enable-prefix-caching` | ALWAYS — free win for agents |
| `--kv-cache-dtype fp8` | When context is long / memory tight |
| `--speculative-model PATH --num-speculative-tokens 5` | When batch size is small (1-4) |
| `--enable-auto-tool-choice --tool-call-parser qwen3_coder` | ALWAYS for tool-calling agents |
| `--reasoning-parser deepseek_r1` | For Nemotron reasoning mode |

## GPU sizing reference

| Model | Min GPU memory | Notes |
|-------|----------------|-------|
| Qwen3-8B (BF16) | 16 GB | Single 4090 / L4 / A10 |
| Qwen3-8B (FP8) | 10 GB | Use `--quantization fp8` |
| Nemotron-Nano-3-30B-A3B (BF16) | 40 GB | Single A100 40 GB / H100 |
| Nemotron-Nano-3-30B-A3B (FP8) | ~24 GB | Fits on RTX 6000 Ada |
