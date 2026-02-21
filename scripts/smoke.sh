#!/usr/bin/env bash
set -euo pipefail

SMOKE_CLEANUP="${SMOKE_CLEANUP:-none}"   # none | down | down-v

SMOKE_USER="${SMOKE_USER:-admin}"
SMOKE_PASS="${SMOKE_PASS:-admin}"

cleanup() {
  case "$SMOKE_CLEANUP" in
    down)
      echo "🧹 Cleanup: docker compose down"
      docker compose down >/dev/null
      ;;
    down-v)
      echo "🧹 Cleanup: docker compose down -v (WIPE DB)"
      docker compose down -v >/dev/null
      ;;
    none|"")
      ;;
    *)
      echo "✘ Invalid SMOKE_CLEANUP=$SMOKE_CLEANUP (use none|down|down-v)"
      ;;
  esac
}

trap cleanup EXIT

echo "=== QHSE SUPPLYCHAIN SMOKE TEST (compose network) ==="
echo

echo "[0] Bringing stack up (db, api, worker, prometheus)..."
docker compose up -d db api worker prometheus >/dev/null
echo "✔ compose up done"

echo "[1] Waiting API (inside compose network)..."
for i in {1..30}; do
  if docker compose exec -T api python - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=2)
PY
  then
    echo "✔ API reachable"
    break
  fi
  sleep 1
  if [[ $i -eq 30 ]]; then
    echo "✘ API not reachable inside container"
    echo "  Tip: docker compose logs api --tail=200"
    exit 1
  fi
done

echo "[2] Checking API metrics..."
docker compose exec -T api python - <<'PY' >/dev/null
import urllib.request
txt = urllib.request.urlopen("http://127.0.0.1:8000/metrics", timeout=3).read().decode()
assert "http_requests_total" in txt
PY
echo "✔ API metrics exposed"

echo "[3] Checking Worker metrics (service-to-service)..."
# IMPORTANT: use service name "worker", not 127.0.0.1 (which would mean "api container itself")
docker compose exec -T api python - <<'PY' >/dev/null
import urllib.request
txt = urllib.request.urlopen("http://worker:9100/metrics", timeout=3).read().decode()
assert "worker_poll_iterations_total" in txt
PY
echo "✔ Worker metrics exposed"

echo "[4] Checking Prometheus targets (service-to-service)..."
for i in {1..30}; do
  if docker compose exec -T api python - <<'PY' >/dev/null 2>&1
import json, urllib.request
data = urllib.request.urlopen("http://prometheus:9090/api/v1/targets", timeout=3).read().decode()
j = json.loads(data)
targets = j.get("data", {}).get("activeTargets", [])
assert any(t.get("health") == "up" for t in targets), "no targets with health=up"
PY
  then
    echo "✔ Prometheus sees targets UP"
    break
  fi
  sleep 1
  if [[ $i -eq 30 ]]; then
    echo "✘ Prometheus still sees no targets UP"
    echo "  Debug (first 1000 chars):"
    docker compose exec -T prometheus sh -lc 'wget -qO- http://localhost:9090/api/v1/targets | head -c 1000; echo'
    exit 1
  fi
done

echo "[5] Login (static demo user ${SMOKE_USER})..."
TOKEN="$(
  docker compose exec -T api python - <<PY
import json, urllib.request
url = "http://127.0.0.1:8000/auth/login"
payload = json.dumps({"username":"$SMOKE_USER","password":"$SMOKE_PASS"}).encode()
req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"}, method="POST")
resp = urllib.request.urlopen(req, timeout=3).read().decode()
print(json.loads(resp)["access_token"].strip())
PY
)"
echo "✔ Token obtained"

echo "[6] Create Supplier..."
SUPPLIER_ID="$(
  docker compose exec -T -e TOKEN="$TOKEN" api python - <<'PY'
import os, json, urllib.request
from urllib.error import HTTPError

token = os.environ["TOKEN"].strip()
url = "http://127.0.0.1:8000/suppliers"
payload = json.dumps({"name":"SMOKE Supplier","certification_expiry":"2030-01-01"}).encode()

req = urllib.request.Request(
  url, data=payload, method="POST",
  headers={"Content-Type":"application/json","Authorization":f"Bearer {token}"},
)

try:
  resp = urllib.request.urlopen(req, timeout=5).read().decode()
  print(json.loads(resp)["id"])
except HTTPError as e:
  print("✘ POST /suppliers failed:", e.code, e.reason)
  print(e.read().decode(errors="replace"))
  raise
PY
)"
echo "✔ Supplier created id=$SUPPLIER_ID"

echo "[7] Create NC..."
docker compose exec -T -e TOKEN="$TOKEN" -e SUPPLIER_ID="$SUPPLIER_ID" api python - <<'PY' >/dev/null
import os, json, urllib.request
from urllib.error import HTTPError

token = os.environ["TOKEN"].strip()
supplier_id = int(os.environ["SUPPLIER_ID"])
url = "http://127.0.0.1:8000/ncs"
payload = json.dumps({"supplier_id":supplier_id,"severity":"high","description":"smoke nc"}).encode()

req = urllib.request.Request(
  url, data=payload, method="POST",
  headers={"Content-Type":"application/json","Authorization":f"Bearer {token}"},
)

try:
  urllib.request.urlopen(req, timeout=5).read()
except HTTPError as e:
  print("✘ POST /ncs failed:", e.code, e.reason)
  print(e.read().decode(errors="replace"))
  raise
PY
echo "✔ NC created"

echo "[8] Checking worker job metric present..."
docker compose exec -T api python - <<'PY' >/dev/null
import urllib.request
txt = urllib.request.urlopen("http://worker:9100/metrics", timeout=3).read().decode()
assert "worker_jobs_processed_total" in txt
PY
echo "✔ Worker job metric present"

echo
echo "=== SMOKE TEST PASSED ✅ ==="