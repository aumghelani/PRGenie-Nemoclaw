#!/usr/bin/env bash
# Run ONCE on the GPU host (Brev / WSL / cloud Linux).
# Idempotent — safe to re-run if interrupted.
set -euo pipefail

echo "[1/5] Checking NVIDIA driver…"
nvidia-smi || { echo "ERROR: nvidia-smi not found. Are you on a GPU box?"; exit 1; }

echo "[2/5] Installing uv (fast Python installer)…"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck source=/dev/null
  source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

echo "[3/5] Creating Python 3.12 venv at ~/vllm-env…"
if [ ! -d "$HOME/vllm-env" ]; then
  uv venv --python 3.12 "$HOME/vllm-env"
fi
# shellcheck source=/dev/null
source "$HOME/vllm-env/bin/activate"

echo "[4/5] Installing vLLM (precompiled wheel) + flashinfer + extras…"
VLLM_USE_PRECOMPILED=1 uv pip install vllm
uv pip install flashinfer-python --extra-index-url https://flashinfer.ai/whl/cu124/torch2.5/ || true
uv pip install "huggingface_hub[cli]" hf_transfer

echo "[5/5] Logging into Hugging Face (paste token if prompted)…"
if [ -z "${HF_TOKEN:-}" ]; then
  huggingface-cli login || true
else
  echo "$HF_TOKEN" | huggingface-cli login --token-stdin
fi

echo
echo "DONE. Activate the env in future shells with:"
echo "  source \$HOME/vllm-env/bin/activate"
echo
echo "Next: bash 01_smoke_test.sh"
