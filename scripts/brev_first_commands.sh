#!/usr/bin/env bash
# Run this on the Brev instance immediately after SSH'ing in.
# Tells us GPU + disk + what's pre-installed, so we know which install
# steps to skip.
#
# Usage on Brev:
#   curl -sLO https://raw.githubusercontent.com/<your-fork>/PRDEMO/main/scripts/brev_first_commands.sh
#   bash brev_first_commands.sh
#
# OR just paste these commands directly into the SSH session.
set +e   # we want all checks to run even if some fail

echo "========== HARDWARE =========="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv 2>/dev/null \
  || echo "nvidia-smi MISSING"

echo
echo "========== OS =========="
. /etc/os-release && echo "$PRETTY_NAME"

echo
echo "========== DISK (home) =========="
df -h ~ | tail -1

echo
echo "========== RAM =========="
free -h | head -2

echo
echo "========== TOOLCHAINS =========="
for cmd in python3 pip uv vllm node npm docker podman openshell nemoclaw nat aiq aiqtoolkit huggingface-cli git curl; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ver=$("$cmd" --version 2>&1 | head -1)
    printf "  %-15s ✓  %s\n" "$cmd" "$ver"
  else
    printf "  %-15s ✗  (missing)\n" "$cmd"
  fi
done

echo
echo "========== Python venv at ~/vllm-env =========="
if [ -d "$HOME/vllm-env" ]; then
  echo "  EXISTS (skip 00_install.sh re-run unless intentional)"
  source "$HOME/vllm-env/bin/activate" 2>/dev/null
  python -c "import vllm; print('  vllm:', vllm.__version__)" 2>/dev/null || echo "  vllm not importable"
  python -c "import openai; print('  openai:', openai.__version__)" 2>/dev/null || true
  deactivate 2>/dev/null
else
  echo "  NOT yet created — need to run 00_install.sh"
fi

echo
echo "========== PORT 5000 currently bound? =========="
ss -tlnp 2>/dev/null | grep -E ':5000\b' || echo "  free"

echo
echo "========== DECISION TABLE =========="
echo "If the toolchain check above shows:"
echo "  vllm = ✗   → run: bash 00_install.sh   (10-15 min)"
echo "  vllm = ✓   → skip install, go straight to: bash 99_baseline_only.sh"
echo "  openshell + nemoclaw = ✓ → bonus: real NemoClaw demo path open"
echo
echo "Paste the OUTPUT ABOVE back to your laptop for review."
