# QHSE / Supply Chain Demo (FastAPI + Outbox + Audit)

This repository is a compact, production-minded demo of a QHSE / Supply Chain backend focused on **reliability over scalability**.

It models a minimal supplier & non-conformity workflow and demonstrates an event-driven architecture where business changes are **durably captured, processed idempotently, and fully auditable** — without introducing a message broker yet.

## Why this exists

Traditional supply chain processes often rely on fragmented tools and manual steps, which makes it hard to maintain:
- consistent supplier qualification & monitoring,
- traceability of operational decisions,
- fast and verifiable reaction to non-conformities (QHSE).

This demo shows a pragmatic approach: **centralize core entities (Suppliers, Non-Conformities), emit domain events transactionally, process them safely, and expose operational KPIs**.

## Key characteristics

- **Transactional Outbox Pattern**: domain events are written in the same DB transaction as business data.
- **Idempotent polling worker**: events are processed at-least-once with deduplication (`processed_events`).
- **Append-only audit trail**: every handled event leaves an immutable record (`audit_log`).
- **Operational KPIs**: `/kpi` reports NC counts, outbox health, and suppliers at risk (expired certification or open high NC).
- **Demo scripts**: `./reset_demo.sh` and `./demo.sh` to reproduce the workflow end-to-end.

## Architecture (high level)

Client → FastAPI → DB (business + outbox)
                    |
                    v
               worker.py (polling)
                    |
                    v
           audit_log + processed_events

- Outbox e dati business condividono la stessa transazione
- Worker idempotente evita duplicazioni
- Audit trail append-only garantisce tracciabilità

---

## Cosa dimostra (in pratica)

- Gestione **Supplier** e **NonConformity**
- Creazione NC → evento `NC_CREATED` in Outbox (transazionale)
- Chiusura NC → evento `NC_CLOSED`
- Aggiornamento certificazione → evento `SUPPLIER_CERT_UPDATED`
- Worker idempotente con deduplica su `processed_events`
- Audit trail persistente su `audit_log`
- Endpoint `/kpi` con metriche operative e rischio fornitore

---

## KPI disponibili

`GET /kpi`

Restituisce:

- `nc_open`
- `nc_open_high`
- `nc_closed`
- `outbox_pending`
- `outbox_failed`
- `suppliers_at_risk`
- `audit_events_total`

### Regola rischio fornitore

Un fornitore è "a rischio" se:

- certificazione scaduta  
**oppure**
- almeno una NC `high` aperta

---

## Requisiti

- Python 3.12+
- (opzionale) `sqlite3` CLI

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi "uvicorn[standard]" sqlalchemy pydantic
python scripts/init_db.py
```

## Avvio API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000


Health check:
curl -s http://127.0.0.1:8000/health

## Demo automatica (consigliata)

Esegue workflow completo:
./reset_demo.sh
./demo.sh


Mostra:
- Creazione Supplier
- Creazione NC (severity=low)
- Consumo evento NC_CREATED
- Chiusura NC
- Aggiornamento certificazione via PATCH
- KPI che passa da suppliers_at_risk=0 a 1

Demo manuale (API → Outbox → Worker → Audit)
1) Crea fornitore
curl -s -X POST http://127.0.0.1:8000/suppliers \
  -H "Content-Type: application/json" \
  -d '{"name":"Beta Metals","certification_expiry":"2026-06-30"}'

2) Crea NC
curl -s -X POST http://127.0.0.1:8000/ncs \
  -H "Content-Type: application/json" \
  -d '{"supplier_id":1,"severity":"high","description":"Certificato materiale mancante"}'

3) Avvia worker
python worker.py

4) Aggiorna certificazione (PATCH parziale)
curl -s -X PATCH http://127.0.0.1:8000/suppliers/1/certification \
  -H "Content-Type: application/json" \
  -d '{"certification_expiry":"2020-01-01"}'

## Verifica DB (opzionale)
sqlite3 qhse_demo.sqlite3 "select id,event_type,status from outbox_events;"
sqlite3 qhse_demo.sqlite3 "select id,action,entity_type,entity_id from audit_log;"

## Decisioni architetturali

Outbox pattern
Evento persistito nella stessa transazione dei dati business.

Worker idempotente
Deduplica tramite tabella processed_events.

Audit trail append-only
Registro verificabile delle azioni di sistema.

## Nota
Il design è broker-agnostico: il worker polling può essere sostituito da un message broker (Kafka, RabbitMQ, ecc.) senza modificare il modello dati o il pattern Outbox.
# Reliability Guarantees

This demo intentionally prioritizes **correctness and traceability**
over horizontal scalability.

## Delivery Semantics

-   **At-least-once processing**
-   Idempotent event handling via `processed_events`
-   Explicit retry policy with bounded attempts
-   Failed events are visible and measurable via KPI

## Transactional Consistency

-   Domain data and Outbox events share the same database transaction.
-   Either both are committed or both are rolled back.
-   No "ghost events" and no "invisible state changes".

## Idempotency Strategy

-   Each event carries a stable `event_id` (UUID).
-   `processed_events` enforces uniqueness on `event_id`.
-   Reprocessing the same event does not duplicate side effects.

## Auditability

-   Every handled event produces an append-only audit record.
-   No destructive updates in `audit_log`.
-   Operational decisions are verifiable post‑factum.

## Failure Policy

-   Unknown or failing events increment `attempts`.
-   Events transition to `FAILED` after a bounded number of retries.
-   Failed events are observable via `/kpi`.

These guarantees are verified by automated tests in the repository.
