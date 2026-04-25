# Brev Launchable Configuration — Tier 2: Performance & Scale

Use these settings when creating the Launchable in the Brev Console.

## Step 1: Files & Runtime
- **Code source:** Git repository → (your hackathon starter repo, or empty sandbox)
- **Runtime mode:** VM Mode (Ubuntu 22.04 with Docker/Python/CUDA)

## Step 2: Environment Configuration
- **Setup script:** Paste contents of `setup.sh` from this directory
- Full SSH access enabled

## Step 3: Jupyter & Networking
- **Jupyter:** Enabled (JupyterLab one-click)
- **Networking:**
  - Port 8000 (vLLM API) — Cloudflare tunnel
  - SSH enabled for tmux/nvtop workflows

## Step 4: Compute Selection
- **GPU:** 2× NVIDIA A100 80GB (preferred) or 2× NVIDIA H100
- **Disk:** 300GB (8B + 70B model weights ~155GB + quantized variants + workspace)
- **Filter by:** Multi-GPU availability, then VRAM

## Step 5: Final Review
- **Name:** `toa-hackathon-performance`
- **Visibility:** Link Sharing
- **Description:** "TOA vLLM/LLM-D Hackathon — Performance Track. Pre-loaded with Llama 3.1 8B + 70B, quantization tools, speculative decoding configs, and benchmarking scripts."

## Tracks Served
- Track 1: The Lean Inference Challenge (quantization/optimization)
- Track 3: Speculative Futures (speculative decoding)
- Track 6: Performance Tuning & Evaluation (Builder/Deep Tech lanes)
