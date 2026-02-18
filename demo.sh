#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
DB_FILE="${DB_FILE:-qhse_demo.sqlite3}"

say() { echo -e "\n=== $* ==="; }

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1"; exit 1; }
}

need curl
need sqlite3

say "Health check"
if ! curl -fsS "$BASE_URL/health" >/dev/null; then
  echo "ERROR: API not reachable at $BASE_URL"
  echo "Start it with:"
  echo "  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
  exit 1
fi
curl -s "$BASE_URL/health" ; echo

say "Create supplier (or reuse if already exists)"
SUPPLIER_JSON=$(curl -s -X POST "$BASE_URL/suppliers" \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Supplier","certification_expiry":"2026-12-31"}' || true)

echo "$SUPPLIER_JSON"

# Extract supplier_id:
# - if created: JSON contains "id":N
# - if already exists: API returns {"detail":"Supplier name already exists"}
SUPPLIER_ID=$(echo "$SUPPLIER_JSON" | sed -n 's/.*"id":[ ]*\([0-9][0-9]*\).*/\1/p' | head -n1 || true)

if [[ -z "${SUPPLIER_ID:-}" ]]; then
  say "Supplier already exists: resolve id from DB"
  SUPPLIER_ID=$(sqlite3 "$DB_FILE" "select id from suppliers where name='Demo Supplier' limit 1;")
fi

echo "Using supplier_id=$SUPPLIER_ID"

say "Create NC (generates outbox event)"
NC_JSON=$(curl -s -X POST "$BASE_URL/ncs" \
  -H "Content-Type: application/json" \
  -d "{\"supplier_id\":$SUPPLIER_ID,\"severity\":\"low\",\"description\":\"Demo NC: missing material certificate at inbound inspection\"}")
echo "$NC_JSON"

NC_ID=$(echo "$NC_JSON" | sed -n 's/.*"id":[ ]*\([0-9][0-9]*\).*/\1/p' | head -n1 || true)
if [[ -z "${NC_ID:-}" ]]; then
  echo "ERROR: could not extract nc_id from response"
  exit 1
fi
echo "Using nc_id=$NC_ID"

say "Outbox events (latest)"
sqlite3 "$DB_FILE" "select id,event_type,status,attempts,created_at from outbox_events order by id desc limit 5;"

say "Run worker once (2 seconds)"
python app.worker.py >/dev/null 2>&1 & WPID=$!
sleep 2
kill "$WPID" >/dev/null 2>&1 || true
wait "$WPID" >/dev/null 2>&1 || true
echo "(worker stopped)"

say "Outbox events after worker"
sqlite3 "$DB_FILE" "select id,event_type,status,attempts,processed_at from outbox_events order by id desc limit 5;"

say "Audit log (latest)"
sqlite3 "$DB_FILE" "select id,action,entity_type,entity_id,created_at from audit_log order by id desc limit 5;"

say "KPI dashboard"
curl -s "$BASE_URL/kpi" ; echo

say "Close NC (workflow) -> generates outbox event"
curl -s -X PATCH "$BASE_URL/ncs/$NC_ID/close" ; echo

say "Force supplier at risk: PATCH certification_expiry in the past (API)"
curl -s -X PATCH "$BASE_URL/suppliers/$SUPPLIER_ID/certification" \
  -H "Content-Type: application/json" \
  -d '{"certification_expiry":"2020-01-01"}' ; echo

say "Run worker once (2 seconds) to process SUPPLIER_CERT_UPDATED"
python app.worker.py >/dev/null 2>&1 & WPID=$!
sleep 2
kill "$WPID" >/dev/null 2>&1 || true
wait "$WPID" >/dev/null 2>&1 || true
echo "(worker stopped)"

say "Supplier detail (should be at risk)"
curl -s "$BASE_URL/suppliers/$SUPPLIER_ID" ; echo

say "KPI dashboard (after forcing risk) -> suppliers_at_risk should be 1"
curl -s "$BASE_URL/kpi" ; echo

say "DONE"
