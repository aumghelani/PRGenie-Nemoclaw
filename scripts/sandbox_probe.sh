#!/usr/bin/env bash
# Discovery probe — run INSIDE the NemoClaw sandbox via:
#   openshell sandbox exec -- /workspace/PRDEMO/scripts/sandbox_probe.sh
# (or wherever PRDEMO landed in the sandbox)
set +e

echo "=== where am I ==="
pwd
whoami
hostname

echo
echo "=== PRDEMO upload location ==="
ls -la ~/PRDEMO 2>/dev/null | head -10
ls -la /workspace/PRDEMO 2>/dev/null | head -10
ls -la /home/sandbox/PRDEMO 2>/dev/null | head -10

echo
echo "=== python ==="
which python3 && python3 --version
which pip3 && pip3 --version

echo
echo "=== which port is the OpenAI proxy ==="
for p in 18791 18792 8000 4444; do
  echo "--- port $p /v1/models ---"
  curl -s --max-time 3 "http://localhost:$p/v1/models" | head -c 400
  echo
done

echo
echo "=== listening ports ==="
ss -tlnp 2>/dev/null | head -10
