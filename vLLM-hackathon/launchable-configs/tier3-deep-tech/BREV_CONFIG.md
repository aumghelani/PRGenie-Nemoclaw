# Brev Launchable Configuration — Tier 3: Deep Tech / Inference at Scale

Use these settings when creating the Launchable in the Brev Console.

## Step 1: Files & Runtime
- **Code source:** Git repository → (your hackathon starter repo, or empty sandbox)
- **Runtime mode:** VM Mode (Ubuntu 22.04 with Docker/Python/CUDA)

## Step 2: Environment Configuration
- **Setup script:** Paste contents of `setup.sh` from this directory
- Full SSH access enabled

## Step 3: Jupyter & Networking
- **Jupyter:** Enabled
- **Networking:**
  - Port 8000 (vLLM / llm-d gateway) — Cloudflare tunnel
  - Port 9090 (Prometheus metrics, optional) — Cloudflare tunnel
  - SSH enabled for kubectl, k9s, tmux workflows

## Step 4: Compute Selection
- **GPU:** 4× NVIDIA A100 80GB (preferred) or 4× NVIDIA H100
- **Disk:** 400GB (model weights + Kubernetes images + workspace)
- **Filter by:** Multi-GPU availability (4+ GPUs), then VRAM

## Step 5: Final Review
- **Name:** `toa-hackathon-deep-tech`
- **Visibility:** Link Sharing
- **Description:** "TOA vLLM/LLM-D Hackathon — Deep Tech Track. Pre-loaded with Llama 3.1 8B + 70B, full llm-d stack, Kubernetes tooling, disaggregated prefill/decode configs, and monitoring."

## Tracks Served
- Track 4: Inference at Scale (Kubernetes deployment)
- Track 1: Lean Inference (Deep Tech lane)
- Track 3: Speculative Futures (Deep Tech lane)
