#!/usr/bin/env bash
# Find PRDEMO + figure out which auth token unlocks the OpenAI proxy on port 18791.
set +e

DASHBOARD_TOKEN="20fcfd9f01953d93c3f13ff6c6679cbfc9053f674a43588b1f4106172642e81d"
NVIDIA_KEY="${NVIDIA_API_KEY:-}"

echo "=== where is PRDEMO inside sandbox ==="
find / -maxdepth 5 -name "PRDEMO" -type d 2>/dev/null | head -5
ls /sandbox/ 2>/dev/null
ls / 2>/dev/null | grep -i -E "prdemo|workspace|home" | head -5

echo
echo "=== look for any NemoClaw config / token files in sandbox ==="
find / -maxdepth 5 -type f \( -name "*token*" -o -name "credentials*" -o -name "config.yaml" -o -name "config.json" -o -name "nemoclaw*" \) 2>/dev/null | head -10

echo
echo "=== inspect the proxy with NO auth (to see expected scheme) ==="
curl -s -i --max-time 3 http://localhost:18791/v1/models | head -15

echo
echo "=== try dashboard token as Bearer ==="
curl -s --max-time 5 -H "Authorization: Bearer $DASHBOARD_TOKEN" http://localhost:18791/v1/models | head -c 500
echo

echo
echo "=== try NVIDIA_API_KEY as Bearer (if set) ==="
if [ -n "$NVIDIA_KEY" ]; then
  curl -s --max-time 5 -H "Authorization: Bearer $NVIDIA_KEY" http://localhost:18791/v1/models | head -c 500
  echo
else
  echo "NVIDIA_API_KEY not set in sandbox env"
fi

echo
echo "=== env vars in sandbox that look like auth ==="
env | grep -iE "token|key|api|secret|auth" | head -20
