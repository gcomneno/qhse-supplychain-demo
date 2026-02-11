#!/usr/bin/env bash
set -euo pipefail

DB_FILE="${DB_FILE:-qhse_demo.sqlite3}"

echo "Reset demo DB: $DB_FILE"
sqlite3 "$DB_FILE" "delete from processed_events;"
sqlite3 "$DB_FILE" "delete from audit_log;"
sqlite3 "$DB_FILE" "delete from outbox_events;"
sqlite3 "$DB_FILE" "delete from nonconformities;"
sqlite3 "$DB_FILE" "delete from suppliers;"
echo "OK: cleared tables"
